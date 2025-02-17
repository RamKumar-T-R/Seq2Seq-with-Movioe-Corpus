# -*- coding: utf-8 -*-
"""
Created on Thu Jun 29 14:23:06 2023

@author: Ramkumar
"""

# Importing the libraries
import numpy as np
import tensorflow as tf
import re
import time


# Part-1: Data Preprocessing


lines = open('dataset/movie_lines.txt', encoding = 'utf-8', errors = 'ignore').read().split('\n')
conversations = open('D:/NLP-course/Dataset & Models/seq2seq/dataset/movie_conversations.txt', encoding = 'utf-8', errors = 'ignore').read().split('\n')

# Creating the dictionary
id2line = {}
for i in lines:
    _line = i.split(' +++$+++ ')
    if(len(_line) == 5):
        id2line[_line[0]] = _line[4]
        
# Creating a list of conversations
conversation_ids = []
for i in conversations[:-1]:
    _conversation = i.split(' +++$+++ ')[-1][1:-1].replace("'", "").replace(" ", "")
    conversation_ids.append(_conversation.split(","))
    
# Separating the questinos ans answers
questions = []
answers = []
for i in conversation_ids:
    for j in range(len(i)-1):
        questions.append(id2line[i[j]])
        answers.append(id2line[i[j+1]])
        
# Function to clean the raw text
def clean_text(text):
    text = text.lower()
    text = re.sub(r"i'm", "i am", text)
    text = re.sub(r"he's", "he is", text)
    text = re.sub(r"she's", "she is", text)
    text = re.sub(r"that's", "that is", text)
    text = re.sub(r"what's", "what is", text)
    text = re.sub(r"where's", "where is", text)
    text = re.sub(r"\'ll", " will", text)
    text = re.sub(r"\'ve", " have", text)
    text = re.sub(r"\'re", " are", text)
    text = re.sub(r"\'d", " would", text)
    text = re.sub(r"won't", "will not", text)
    text = re.sub(r"can't", "cannot", text)
    text = re.sub(r"[-()\"#/@;:<>{}+=~|.,?!'*]", "", text)
    return text

# Cleaning the question
clean_questions = []
for i in questions:
    clean_questions.append(clean_text(i))

# Cleaning the answer
clean_answers = []
for i in answers:
    clean_answers.append(clean_text(i))    

# Counting the number of occurences of each word
word2count = {}
for i in clean_questions:
    for j in i.split():
        if(j not in word2count):
            word2count[j] = 1
        else:
            word2count[j] += 1

for i in clean_answers:
    for j in i.split():
        if(j not in word2count):
            word2count[j] = 1
        else:
            word2count[j] += 1            
    
# Tokenizing the ansers and questions
threshold = 20
word_number = 0
questionwords2int = {}
for word, count in word2count.items():
    if count >= threshold:
        questionwords2int[word] = word_number
        word_number += 1

word_number = 0
answerwords2int = {}
for word, count in word2count.items():
    if count >= threshold:
        answerwords2int[word] = word_number
        word_number += 1
        
# Adding the last tonekns
tokens = ['<PAD>', '<EOS>', '<OUT>', '<SOS>']
for token in tokens:
    questionwords2int[token] = len(questionwords2int) + 1      
    answerwords2int[token] = len(answerwords2int) + 1
    
# Creating an inverse dictionary for answers only
quesionints2word = {w_i: w for w, w_i in questionwords2int.items()}
answerints2word = {w_i: w for w, w_i in answerwords2int.items()}

# Adding <EOS> in every sentence of clean_answers
for i in range(len(clean_answers)):
    clean_answers[i] += ' <EOS>'
    
# Transforming words to int on questiona and answers
question_to_int = []
for i in clean_questions:
    ints = []
    for j in i.split():
        if(j not in questionwords2int):
            ints.append(questionwords2int['<OUT>'])
        else:
             ints.append(questionwords2int[j])
    question_to_int.append(ints)


answer_to_int = []
for i in clean_answers:
    ints = []
    for j in i.split():
        if(j not in answerwords2int):
            ints.append(answerwords2int['<OUT>'])
        else:
             ints.append(answerwords2int[j])
    answer_to_int.append(ints)
    
# Sorting the questions ans answers using questions
sorted_clean_questions = []
sorted_clean_answers = []
for length in range(1, 25 + 1):
    for i in enumerate(question_to_int):
        if length == len(i[1]):
            sorted_clean_questions.append(i[1])
            sorted_clean_answers.append(answer_to_int[i[0]])


# Part-2: Building the seq2seq model

# Creating the placeholder for inputs ans targets
def model_inputs():
    inputs = tf.placeholder(tf.int32, [None, None], name='input')
    targets = tf.placeholder(tf.int32, [None, None], name='target')
    lr = tf.placeholder(tf.float32, name='learning_rate')
    keep_prob = tf.placeholder(tf.float32, name='keep_prob')
    return inputs, targets, lr, keep_prob

# Preprocessing the targets
def preprocess_targets(targets, word2int, batch_size):
    left_side = tf.fill([batch_size, 1], word2int['<SOS>'])
    right_side = tf.strided_slice(targets, [0, 0], [batch_size, -1], [1, 1])
    preprocessed_targets = tf.concat([left_side, right_side], 1)
    return preprocessed_targets
    
# Creating the Encoder RNN layer
def encoder_rnn(rnn_inputs, rnn_size, num_layers, keep_prob, sequence_length):
    lstm = tf.contrib.rnn.BasicLSTMCell(rnn_size)
    lstm_dropout = tf.contrib.rnn.DropoutWrapper(lstm, input_keep_prob = keep_prob)
    encoder_cell = tf.contrib.rnn.MultiRNNCell([lstm_dropout] * num_layers)
    _, encoder_state = tf.nn.bidirectional_dynamic_rnn(cell_fw = encoder_cell,
                                                       cell_bw = encoder_cell,
                                                       sequence_length = sequence_length,
                                                       inputs = rnn_inputs,
                                                       dtype = tf.float32)
    print(encoder_cell)
    return encoder_state

# Decoding the training set
def decode_training_set(encoder_state, decoder_cell, decoder_embedded_input, sequence_length, decoding_scope, output_function, keep_prob, batch_size):
    #def decode_training_set(encoder_state, decoder_cell, decoder_embedded_input, sequence_length, decoding_scope, output_function, keep_prob, batch_size):
    attention_states = tf.zeros([batch_size, 1, decoder_cell.output_size])
    attention_keys, attention_values, attention_score_function, attention_construct_function = tf.contrib.seq2seq.prepare_attention(attention_states, attention_option = 'bahdanau', num_units = decoder_cell.output_size)
    training_decoder_function = tf.contrib.seq2seq.attention_decoder_fn_train(encoder_state[0], 
                                                                              attention_keys,
                                                                              attention_values,
                                                                              attention_score_function,
                                                                              attention_construct_function,
                                                                              name = 'attn_dec_train')
    decoder_output, _, _ = tf.contrib.seq2seq.dynamic_rnn_decoder(decoder_cell,
                                                                  training_decoder_function, 
                                                                  decoder_embedded_input, 
                                                                  sequence_length,
                                                                  scope = decoding_scope)
    decoder_output_dropout = tf.nn.dropout(decoder_output, keep_prob)
    return output_function(decoder_output_dropout)

# Decoding the test/validation set
def decode_test_set(encoder_state, decoder_cell, decoder_embeddings_matrix, sos_id, eos_id, maximum_length, num_words, sequence_length, decoding_scope, output_function, keep_prob, batch_size):
    attention_states = tf.zeros([batch_size, 1, decoder_cell.output_size])
    attention_keys, attention_values, attention_score_function, attention_construct_function = tf.contrib.seq2seq.prepare_attention(attention_states, attention_option = 'bahdanau', num_units = decoder_cell.output_size)
    test_decoder_function = tf.contrib.seq2seq.attention_decoder_fn_inference(output_function,
                                                                              encoder_state[0], 
                                                                              attention_keys,
                                                                              attention_values,
                                                                              attention_score_function,
                                                                              attention_construct_function,
                                                                              decoder_embeddings_matrix, 
                                                                              sos_id, 
                                                                              eos_id, 
                                                                              maximum_length, 
                                                                              num_words,
                                                                              name = 'attn_dec_inf')
    test_predictions, _, _ = tf.contrib.seq2seq.dynamic_rnn_decoder(decoder_cell,
                                                                    test_decoder_function, 
                                                                    scope = decoding_scope)
    return test_predictions

# Creating the decoder RNN
def decoder_rnn(decoder_embedded_input, decoder_embeddings_matrix, encoder_state, num_words, sequence_length, rnn_size, num_layers, word2int, keep_prob, batch_size):
    with tf.variable_scope('decoding') as decoding_scope:
        lstm = tf.contrib.rnn.BasicLSTMCell(rnn_size)
        lstm_dropout = tf.contrib.rnn.DropoutWrapper(lstm, input_keep_prob = keep_prob)
        decoder_cell = tf.contrib.rnn.MultiRNNCell([lstm_dropout] * num_layers)
        weights = tf.truncated_normal_initializer(stddev = 0.1)
        biases = tf.zeros_initializer()
        output_function = lambda x: tf.contrib.layers.fully_connected(x,
                                                                      num_words,
                                                                      None,
                                                                      scope = decoding_scope,
                                                                      weights_initializer = weights,
                                                                      biases_initializer = biases)
        training_predictions = decode_training_set(encoder_state,
                                                   decoder_cell,
                                                   decoder_embedded_input,
                                                   sequence_length,
                                                   decoding_scope,
                                                   output_function,
                                                   keep_prob,
                                                   batch_size)
        decoding_scope.reuse_variables()
        test_predictions = decode_test_set(encoder_state,
                                           decoder_cell,
                                           decoder_embeddings_matrix,
                                           word2int['<SOS>'],
                                           word2int['<EOS>'],
                                           sequence_length - 1,
                                           num_words,
                                           sequence_length,  # this is created by me  # correct
                                           decoding_scope,
                                           output_function,
                                           keep_prob,
                                           batch_size)
    return training_predictions, test_predictions
    
# Building the seq2seq model
def seq2seq_model(inputs, targets, keep_prob, batch_size, sequence_length, answers_num_words, questions_num_words, encoder_embedding_size, decoder_embedding_size, rnn_size, num_layers, questionswords2int):
    encoder_embedded_input = tf.contrib.layers.embed_sequence(inputs, 
                                                               answers_num_words + 1, 
                                                               encoder_embedding_size, 
                                                               initializer = tf.random_uniform_initializer(0, 1))
    encoder_state = encoder_rnn(encoder_embedded_input, rnn_size, num_layers, keep_prob, sequence_length)
    preprocessed_targets = preprocess_targets(targets, questionswords2int, batch_size)
    decoder_embeddings_matrix = tf.Variable(tf.random_uniform([questions_num_words + 1, decoder_embedding_size], 0, 1))
    decoder_embedded_input = tf.nn.embedding_lookup(decoder_embeddings_matrix, preprocessed_targets)
    training_predictions, test_predictions = decoder_rnn(decoder_embedded_input, 
                                                         decoder_embeddings_matrix, 
                                                         encoder_state,
                                                         questions_num_words,
                                                         sequence_length,
                                                         rnn_size,
                                                         num_layers,
                                                         questionswords2int,
                                                         keep_prob,
                                                         batch_size)
    return training_predictions, test_predictions

# Part-3: Training the seq2seq model

# Setting the hyperparameter
epochs = 1   #100
batch_size = 256  #64
rnn_size = 512
num_layers = 3
encoding_embedding_size = 512
decoding_embedding_size = 512
learning_rate = 0.01
learning_rate_decay = 0.5
min_learning_rate = 0.0001
keep_probability = 0.5

# Disabling the eager execution
#tf.compat.v1.disable_eager_execution()

# Defining a session
#tf.reset_default_graph()
session = tf.InteractiveSession() #session = tf.InteractiveSession()

# Loading the model inputs
inputs, targets, lr, keep_prob = model_inputs()
    
# Setting the sequence length
sequence_length = tf.placeholder_with_default(25, None, name = 'sequence_length')

# Getting the shape of inputs tensor
input_shape = tf.shape(inputs)
# Getting the training and test predictions
training_predictions, test_predictions = seq2seq_model(tf.reverse(inputs, [-1]), 
                                                       targets,
                                                       keep_prob,
                                                       batch_size, 
                                                       sequence_length,
                                                       len(answerwords2int),
                                                       len(questionwords2int),
                                                       encoding_embedding_size,
                                                       decoding_embedding_size,
                                                       rnn_size,
                                                       num_layers,
                                                       questionwords2int)
# Setting the Loss Error, the Optimizer and Gradient Clipping
with tf.name_scope("Optimization"):
    loss_error = tf.contrib.seq2seq.sequence_loss(training_predictions,
                                                  targets,
                                                  tf.ones([input_shape[0], sequence_length]))
    optimizer = tf.train.AdamOptimizer(learning_rate)
    gradients = optimizer.compute_gradients(loss_error)
    clipped_gradient = [(tf.clip_by_value(grad_tensor, -5., 5.), grad_variable) for grad_tensor, grad_variable in gradients if grad_tensor is not None]
    optimizer_gradient_clipping = optimizer.apply_gradients(clipped_gradient)
                                                  
# Padding the sequence using the <PAD> token
def apply_padding(batch_of_sequences, word2int):
    max_sequence_length = max([len(sequence) for sequence in batch_of_sequences])
    return [sequence + [word2int['<PAD>']] * (max_sequence_length - len(sequence)) for sequence in batch_of_sequences] 

# Splitting the data(questions & answers) into batches
def split_into_batches(questions, answers, batch_size):
    for batch_index in range(0, len(questions) // batch_size):
        start_index = batch_index * batch_size
        questions_in_batch = questions[start_index: start_index + batch_size]
        answers_in_batch = answers[start_index: start_index + batch_size]
        padded_questions_in_batch = apply_padding(questions_in_batch, questionwords2int)
        padded_answers_in_batch = apply_padding(answers_in_batch, answerwords2int)
        padded_questions_in_batch = np.array(padded_questions_in_batch)
        padded_answers_in_batch = np.array(padded_answers_in_batch)
        yield padded_questions_in_batch, padded_answers_in_batch
        
# Splitting the questions and answers into training and validation sets
training_validation_split = int(len(sorted_clean_questions) * 0.15)
training_questions = sorted_clean_questions[training_validation_split:]
validation_questions = sorted_clean_questions[: training_validation_split]
training_answers = sorted_clean_answers[training_validation_split:]
validation_answers = sorted_clean_answers[: training_validation_split]

# Training
batch_index_check_training_loss = 100
batch_index_check_validation_loss = ((len(training_questions) // batch_size //2 ) -1 )
total_training_loss_error = 0
list_validation_loss_error = []
early_stopping_check = 0
early_stopping_stop = 1000
checkpoint = "./chatbot_weights.ckpt"
session.run(tf.global_variables_initializer())
for epoch in range(1, epochs+1):
    for batch_index, (padded_questions_in_batch, padded_answers_in_batch) in enumerate(split_into_batches(training_questions, training_answers, batch_size)):
        starting_time = time.time()
        _, batch_training_loss_error = session.run([optimizer_gradient_clipping, loss_error], {inputs: padded_questions_in_batch,
                                                                                               targets: padded_answers_in_batch,
                                                                                               lr: learning_rate,
                                                                                               sequence_length: padded_answers_in_batch.shape[1],
                                                                                               keep_prob: keep_probability }
                                                   )
        total_training_loss_error += batch_training_loss_error
        ending_time = time.time()
        batch_time = ending_time - starting_time
        print("Training time for batch", batch_index, "is: ", batch_time)
        if batch_index % batch_index_check_training_loss == 0:
            print('Epoch: {:>3}/{}, Batch: {:>4}/{}, Training Loss Error: {:>6.3f}, Training Time on 100 Batches: {:d} seconds'.format(epoch,
                                                                                                                                         epochs,
                                                                                                                                         batch_index,
                                                                                                                                         len(training_questions) // batch_size,
                                                                                                                                         total_training_loss_error / batch_index_check_training_loss,
                                                                                                                                         int(batch_time * batch_index_check_training_loss)
                                                                                                                                         )
                    )
            total_training_loss_error = 0
        if batch_index % batch_index_check_validation_loss == 0 and batch_index > 0:
            total_validation_loss_error = 0
            starting_time = time.time()
            for batch_index_validation, (padded_question_in_batch, padded_answers_in_batch) in enumerate(split_into_batches(validation_questions, validation_answers, batch_size)):
                batch_validation_loss_error = session.run(loss_error, {inputs: padded_questions_in_batch,
                                                                       targets: padded_answers_in_batch,
                                                                       lr: learning_rate,
                                                                       sequence_length: padded_answers_in_batch.shape[1],
                                                                       keep_prob: 1}
                                                           )
                total_validation_loss_error += batch_validation_loss_error
            ending_time = time.time()
            batch_time = ending_time - starting_time
            average_validation_loss_error = total_validation_loss_error/ (len(validation_questions)/ batch_size)
            print('Validation Loss Error: {:>6.3f}, Batch Validation Time; {:d} seconds'.format(average_validation_loss_error, int(batch_time)))
            learning_rate *= learning_rate_decay
            if learning_rate < min_learning_rate:
                learning_rate = min_learning_rate
            list_validation_loss_error.append(average_validation_loss_error)
            if average_validation_loss_error <= min(list_validation_loss_error):
                print('I speak better now !')
                early_stopping_check = 0
                saver = tf.train.Saver()
                saver.save(session, checkpoint)
            else:
                print("I'm getting trained")
                early_stopping_check += 1
                if early_stopping_check == early_stopping_stop:
                    break
    if early_stopping_check == early_stopping_stop:
        print('This is the best vesion of me')
        break
print('Training is over')


####### Part-4: Testing the SEQ2SEQ model

# Loading the weights and running the session
checkpoint = "./chatbot_weights.ckpt"
session = tf.InteractiveSession()
session.run(tf.global_variables_initializer())
from tensorflow.python.tools.inspect_checkpoint import print_tensors_in_checkpoint_file
print_tensors_in_checkpoint_file(file_name=checkpoint, tensor_name='', all_tensors=False)
saver = tf.train.Saver()
saver.restore(session, checkpoint)

# Converting the question into the sequencce of encoding integers
def convert_string2int(question, word2int):
    question = clean_text(question)
    return [word2int.get(word, word2int['<OUT>']) for word in question.split()]

# Setting up the interaction
while(True):
    question = input('You: ')
    if question == 'Goodbye':
        break
    question = convert_string2int(question, questionwords2int)
    question = question + [questionwords2int['<PAD>']] * (20 - len(question))
    fake_batch = np.zeros((batch_size, 20))
    fake_batch[0] = question
    predicted_answer = session.run(test_predictions, {inputs: fake_batch, keep_prob: 0.5})[0]
    answer = ''
    for i in np.argmax(predicted_answer, 1):
        if answerints2word[i] == 'i':
            token = "I"
        elif answerints2word[i] == '<EOS>':
            token = '.'
        elif answerints2word[i] == 'OUT':
            token = 'out'
        else:
            token = ' ' + answerints2word[i]
        answer += token

        if token == '.':
            break
    print('Bot:', answer)











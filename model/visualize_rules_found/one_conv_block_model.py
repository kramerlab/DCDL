import numpy as np
import tensorflow as tf
import os
import sys

class network_one_convolution():

    def __init__(self,
                 name_of_model,
                 learning_rate,
                 number_classes,
                 input_shape,
                 nr_training_iteration,
                 batch_size,
                 print_every,
                 check_every,
                 number_of_kernel,
                 shape_of_kernel,
                 stride,
                 input_channels ,
                 input_binarized,
                 # activation is a sign function sign(x) = -1 if x < 0; 0 if x == 0; 1 if x > 0.
                 activation,
                 use_bias_in_convolution,
                 save_path_model,
                 save_path_logs):
        # Clears the default graph stack and resets the global default graph.

        tf.compat.v1.reset_default_graph()

        # save method parameter as class parameter
        self.learning_rate = learning_rate
        self.classes = number_classes
        self.input_shape = input_shape
        self.nr_training_iteration = nr_training_iteration
        self.batch_size = batch_size
        self.print_every = print_every
        self.check_every = check_every

        self.folder_to_save = save_path_model
        self.save_path_logs = save_path_logs
        self.name_of_model = name_of_model
        self.number_of_kernel = number_of_kernel
        self.shape_of_kernel = shape_of_kernel
        self.stride = stride
        self.input_channels = input_channels
        self.input_binarized = input_binarized
        self.activation = activation
        self.use_bias_in_convolution = use_bias_in_convolution

        # built the graph which is used later
        self.built_graph()

    def built_graph(self):

        self.Input_in_Graph = tf.compat.v1.placeholder(dtype=tf.compat.v1.float32, shape=self.input_shape)
        # True Label are one hot label with shape e.g. [[0,1], ... , [1,0]]
        self.True_Label = tf.compat.v1.placeholder(dtype=tf.compat.v1.float32, shape=[None, self.classes])

        X = tf.compat.v1.reshape(self.Input_in_Graph,(-1, self.input_shape[1], self.input_shape[2], self.input_channels))


        with tf.compat.v1.variable_scope("dcdl_conv_1", reuse=False):
            # get convolution block
            X = tf.compat.v1.layers.conv2d(inputs=X, filters=self.number_of_kernel, kernel_size=self.shape_of_kernel, strides=[
                self.stride, self.stride], padding="same", activation=self.activation, use_bias=False)

        X = tf.compat.v1.layers.flatten(X)

        # fix mapping from convolution result of shape [x] to one hot label [a, b]
        # result of dense layer will be [x.x, y.y]
        init = tf.constant_initializer([1,0])
        self.prediction = tf.compat.v1.layers.dense(X,
                                                    units=self.classes,
                                                    activation= tf.compat.v1.nn.softmax,
                                                    kernel_initializer=init,
                                                    trainable=False,
                                                    use_bias=False )

        # calculate loss
        self.loss = tf.compat.v1.reduce_mean(-tf.compat.v1.reduce_sum(self.True_Label *
                                                tf.compat.v1.log(self.prediction + 1E-10), reduction_indices=[1]))  # + reg2
        # make step with optimizer
        self.step = tf.compat.v1.train.AdamOptimizer(self.learning_rate).minimize(self.loss)

        # map one hot prediction to class prediction
        #  with two classes this is identically  with input[:,[1]]
        #  [[0,1],         [1]
        #   [1,0]     ->   [0]
        #   ...]
        # Update possibility (was not changed to be consistent with existing experiment results):
        # remove arg max function
        # or use the DCDL approach to get the values already at the node self.prediction.

        self.one_hot_out = tf.compat.v1.argmax(self.prediction, 1)
        self.hits = tf.compat.v1.equal(self.one_hot_out, tf.compat.v1.argmax(self.True_Label, 1))
        self.accuracy = tf.compat.v1.reduce_mean(tf.compat.v1.cast(self.hits, tf.compat.v1.float32))

        # Initialize the variables
        self.init = tf.compat.v1.global_variables_initializer()

        # Save model
        self.saver = tf.compat.v1.train.Saver()


    def training(self, train, label_train, val, label_val, loging = True):
        loss_list, val_list = [], []
        with tf.compat.v1.Session() as sess:
            if loging:
                # logs can be visualized in tensorboard.
                # useful for see structure of the graph
                path_to_store_logs = self.save_path_logs# os.path.dirname(sys.argv[0]) + "/logs"
                print(self.save_path_logs)
                writer = tf.compat.v1.summary.FileWriter(path_to_store_logs, session=sess,
                                               graph=sess.graph)  # + self.name_of_model, sess.graph)

            sess.run(self.init)
            best_acc_so_far = 0

            for iteration in range(self.nr_training_iteration):
                # train net

                indices = np.random.choice(len(train), self.batch_size)
                batch_X = train[indices]
                batch_Y = label_train[indices]
                feed_dict = {self.Input_in_Graph: batch_X, self.True_Label: batch_Y}

                _, lo, acc = sess.run([self.step, self.loss, self.accuracy], feed_dict=feed_dict)
                if iteration % self.print_every == 1:
                    print("Iteration: ", iteration, "Acc. at trainset: ", acc, flush=True)

                if iteration % self.check_every == 1:
                    # validate net on train data
                    # Update possibility (was not changed to be consistent with existing experiment results):
                    # 5000 should be a variable which is set in the main script
                    # e.g. size_of_val_used_in_one_step = 5000
                    indices = np.random.choice(len(val), 5000)
                    acc, lo = sess.run([self.accuracy, self.loss], feed_dict={
                        self.Input_in_Graph: val[indices], self.True_Label: label_val[indices]})
                    print("step: ", iteration, 'Accuracy at val_set: ', acc, )

                    loss_list.append(lo)
                    val_list.append(acc)

                    if acc > best_acc_so_far:
                        best_acc_so_far = acc
                        save_path = self.saver.save(sess, self.folder_to_save)
                        print('Path to store parameter: ', save_path)



    def evaluate(self, input, label):
        # get accuracy for a data and label set
        with tf.compat.v1.Session() as sess:
            # load saved model variables
            self.saver.restore(sess, self.folder_to_save)
            # Update possibility (was not changed to be consistent with existing experiment results):
            # use
            # acc = sess.run([self.accuracy], feed_dict={self.Input_in_Graph: input, self.True_Label: label})[0]
            # print("Test Accuracy", self.name_of_model, acc)
            # return acc
            size_test_nn = input.shape[0]
            counter = 0  # biased
            acc_sum = 0
            for i in range(0, size_test_nn, 512):
                start = i
                end = min(start + 512, size_test_nn)
                acc = sess.run([self.accuracy], feed_dict={self.Input_in_Graph: input, self.True_Label: label})[0]
                acc_sum += acc
                counter += 1


            print("Test Accuracy", self.name_of_model, acc_sum / counter)

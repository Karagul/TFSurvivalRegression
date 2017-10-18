# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
import numpy as np
import data_providers
import visualize
import dnn_model
from sklearn.model_selection import train_test_split
from tensorflow.contrib.framework.python.ops.variables import get_or_create_global_step
from tensorflow.python.platform import tf_logging as logging
import tensorflow as tf


flags = tf.app.flags
flags.DEFINE_string('x_data', './Brain_Integ_X.csv',
                    'Directory file with features-data.')
flags.DEFINE_string('y_data', './Brain_Integ_Y.csv',
                    'Directory file with label-values.')
flags.DEFINE_string('ckpt_dir', './ckpt_dir/',
                    'Directory for checkpoint files.')
flags.DEFINE_float('split_ratio', 0.2,
                   'Split ratio for test data.')
flags.DEFINE_float('lr_decay_rate', 0.9,
                   'Learning decaying rate.')
flags.DEFINE_float('beta', 0.01,
                   'Regularizing constant.')
flags.DEFINE_float('dropout', 0.6,
                   'Drop out ratio.')
flags.DEFINE_float('init_lr', 0.001,
                   'Initial learning rate.')
flags.DEFINE_integer('batch_size', 100,
                     'Batch size.')
flags.DEFINE_integer('n_epochs', 500,
                     'Number of epochs.')
flags.DEFINE_integer('n_classes', 1,
                     'Number of classes in case of classification.')
flags.DEFINE_integer('display_step', 100,
                     'Displaying step at training.')
flags.DEFINE_integer('n_layers', 3,
                     'Number of layers.')
flags.DEFINE_integer('n_neurons', 500,
                     'Number of Neurons.')

FLAGS = flags.FLAGS
slim = tf.contrib.slim
split = train_test_split


def main(args):
    """The function for TF-Slim DNN model training.

    This function receives user-given parameters as gflag arguments. Then it
    creates the tensorflow model-graph, defines loss and optimizer. Finally,
    creates a training loop and saves the results and logs in the sub-directory.

    Args:
        args: This brings all gflags given user inputs with default values.

    Returns:
        None
    """

    data_x, data_y = data_providers.data_providers(FLAGS.x_data, FLAGS.y_data)

    # split the train and test data
    x_train, x_test, y_train, y_test = split(data_x, data_y,
                                             test_size=FLAGS.split_ratio,
                                             random_state=420)

    n_obs = x_train.shape[0]
    n_features = x_train.shape[1]

    # Start building the graph
    tf.reset_default_graph()
    with tf.Graph().as_default() as graph:
        logging.set_verbosity(tf.logging.INFO)

        if not tf.gfile.Exists(FLAGS.ckpt_dir):
            tf.gfile.MakeDirs(FLAGS.ckpt_dir)

        n_batches = n_obs / FLAGS.batch_size
        decay_steps = int(FLAGS.n_epochs * n_batches)

        x_batch, y_batch = tf.train.shuffle_batch([x_train, y_train],
                                                  batch_size=FLAGS.batch_size,
                                                  capacity=50000,
                                                  min_after_dequeue=10000,
                                                  num_threads=1,
                                                  allow_smaller_final_batch=True)

        # Create the model and pass the input values batch by batch
        hidden_layers = [FLAGS.n_neurons] * FLAGS.n_layers
        pred, end_points = dnn_model.multilayer_nn_model(x_batch,
                                                         hidden_layers,
                                                         FLAGS.n_classes,
                                                         FLAGS.beta)

        global_step = get_or_create_global_step()

        lr = tf.train.exponential_decay(learning_rate=FLAGS.init_lr,
                                        global_step=global_step,
                                        decay_steps=decay_steps,
                                        decay_rate=FLAGS.lr_decay_rate,
                                        staircase=True)

        # Define loss
        loss = tf.losses.mean_squared_error(tf.squeeze(pred), y_batch)
        tf.losses.add_loss(loss)
        total_loss = tf.losses.get_total_loss()

        tf.summary.scalar('loss', total_loss)

        optimizer = tf.train.GradientDescentOptimizer(learning_rate=lr)

        # create the back-propagation object
        train_op = slim.learning.create_train_op(
            total_loss,
            optimizer,
            clip_gradient_norm=4,   # Gives quick convergence
            check_numerics=True,
            summarize_gradients=True)

        # create the training loop
        final = slim.learning.train(
            train_op,
            FLAGS.ckpt_dir,
            log_every_n_steps=1,
            graph=graph,
            global_step=global_step,
            number_of_steps=FLAGS.n_epochs,
            save_summaries_secs=20,
            startup_delay_steps=0,
            saver=None,
            save_interval_secs=10,
            trace_every_n_steps=1
        )


if __name__ == '__main__':
    tf.app.run()

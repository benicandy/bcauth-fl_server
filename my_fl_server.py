# -*- coding: utf-8 -*-
from my_tff import my_fl
import numpy as np
import tensorflow as tf
from PIL import Image
import os

# ***** FL-Server **************************************
"""
:param li_data_dir: 訓練したいデータを記録したディレクトリのリスト
"""

def _train(mnist_train, mnist_test):
    # mnist_train.shape: (2, )
    # mnist_train[0].shape: (60000, 28, 28)
    # mnist_train[1].shape: (60000, )
    # mnist_train, mnist_test = tf.keras.datasets.mnist.load_data()

    NUM_EXAMPLES_PER_USER = 3000
    BATCH_SIZE = 100


    def get_data_for_digit(source, digit):
        output_sequence = []
        # all_samples: digit と等しいラベルのデータの index 番号のリスト
        # {0, 1, 2}, {3, 4, 5}, {6, 7, 8, 9} の三種類に分割
        if digit != 6:
            all_samples = [i for i, d in enumerate(source[1]) if d == digit or d == digit+1 or d == digit+2]
        else:
            all_samples = [i for i, d in enumerate(source[1]) if d == digit or d == digit+1 or d == digit+2 or d == digit+3]
        for i in range(0, min(len(all_samples), NUM_EXAMPLES_PER_USER), BATCH_SIZE):
            batch_samples = all_samples[i:i + BATCH_SIZE]
            output_sequence.append({
                'x':
                    np.array([source[0][i].flatten() / 255.0 for i in batch_samples],
                            dtype=np.float32),
                'y':
                    np.array([source[1][i]
                            for i in batch_samples], dtype=np.int32)
            })
        return output_sequence


    # federated_train_data =
    #         [num_client][NUM_EXAMPLES_PER_USER / batch_size][x or y](batch_size, data)
    federated_train_data = [get_data_for_digit(mnist_train, d) for d in [0, 3, 6]]
    federated_test_data = [get_data_for_digit(mnist_test, d) for d in [0, 3, 6]]

    model = my_fl.my_training_model(federated_train_data, federated_test_data)
    
    return model


def federated_train(li_data_dir):
    fl_data = []  # 全データ
    for dir in li_data_dir:
        li_file = [f for f in files if os.path.isfile(os.path.join(dir, f))]
        for file in li_file:
            img = np.array(Image.open(dir + file).convert('L')) # img.shape: (28, 28)
            fl_data.append(img)
    
    th = 0.9
    fl_train = fl_data[:len(fl_data)*th]
    fl_test = fl_data[len(fl_data)*th:]
    return _train(fl_train, fl_test)


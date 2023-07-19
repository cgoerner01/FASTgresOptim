import tensorflow as tf
from tensorflow import keras
from keras import losses
import json
import numpy


def get_uncompiled_model(input_shape):
    model = keras.Sequential()
    if input_shape[1] < 64:
        model.add(keras.layers.Dense(64, input_shape=(64,), activation="relu"))
    else:
        model.add(keras.layers.Dense(input_shape[1], input_shape=(input_shape[1],), activation="relu"))
    #model.add(keras.layers.Dropout(0.2))
    model.add(keras.layers.Dense(96, activation="relu"))
    model.add(keras.layers.Dense(64, activation="softmax"))
    return model


class CustomLoss(keras.losses.Loss):
    # not functional
    def __init__(self, labels_path="/Users/chrisgoerner/Documents/BA/FASTgres/labels/25052023_1437.json", query_names=[]):
        super().__init__()
        self.labels_path = labels_path
        self.query_names = query_names

    def call(self, y_true, y_pred):
        # inputs:
        # y_true: actual pre-computer best hint set for query
        # y_pred: hint set predicted by model for a query
        # output: tensor of shape like y_true and y_pred with float values of negative speedup
        speedups = []
        y_true = y_true.numpy()
        y_pred = y_pred.numpy()
        #hs_lookup_dict = dict()
        #for i in range(0,64):
        #    hs_lookup_dict[i] = (1/64)*i
        true_exec_time = 1.
        pred_exec_time = 1.
        for q in range(len(self.query_names)):
            with open(self.labels_path) as labels:
                labels_dict = json.load(labels)
                for key in labels_dict:
                    if key == self.query_names[q]:
                        print("y_true: " + str(y_true[q]))
                        print("y_pred: " + str(y_pred[q]))
                        if str(y_pred[q]) not in labels_dict[key]:
                            print("meh")
                            speedups.append(1.0)
                            break
                        true_exec_time = labels_dict[key][str(y_true[q])]
                        pred_exec_time = labels_dict[key][str(y_pred[q])]
                        speedups.append(-(y_true / y_pred))
        speedups = tf.constant(speedups)
        return speedups
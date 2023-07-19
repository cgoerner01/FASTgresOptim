import argparse
import os.path
import time

import numpy
import numpy as np
import featurize
import utility as u
import json
from copy import deepcopy
from alive_progress import alive_it
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.tree import plot_tree
import matplotlib.pyplot as plt
import score as sc
from hint_sets import HintSet
from featurize import encode_query
from query import Query
from context_heuristic import merge_context_queries
from score import speedup
import sklearn
import tensorflow as tf
from tensorflow import keras
from keras.utils import np_utils
import nn


class QueryObserver:

    def __init__(self, seed: int, context: frozenset, archive: dict, experience: dict,
                 absolute_time_gate: float, relative_time_gate: int, query_path: str, db_string: str,
                 estimators: int, depth: int, learning_rate, min_samples_split):
        # the model part
        self.seed = seed
        self.estimators = estimators
        self.depth = depth
        self.learning_rate = learning_rate
        self.min_samples_split = min_samples_split
        self.archive = archive
        self.context = context
        # query_name -> featurization | label | time
        self.experience = experience
        self.model = None
        # the timeout part
        self.absolute = absolute_time_gate
        self.relative = relative_time_gate

        self.timeout = None
        self.update_timeout()
        self.critical_queries = set()

        self.new_model = None
        self.cooldown = 0
        self.critical = u.tree()
        self.path = query_path
        self.db_string = db_string

    def __str__(self) -> str:
        return "Gradient Boosting Observer (est: {}, d: {}) on Context: {} using {} Experiences and Timeout: {}" \
            .format(self.estimators, self.depth, self.context, len(self.experience.keys()), self.timeout)

    def update_timeout(self) -> None:
        old_timeout = self.timeout  # for debug info
        experienced_time = list()
        for query_name in self.experience:
            experienced_time.append(self.experience[query_name]["time"])
        new_timeout = np.percentile(experienced_time, self.relative)
        self.timeout = max(self.absolute, new_timeout)
        print("Updated context: {} timeout: {} -> {}".format(self.context, old_timeout, new_timeout))
        return

    def train(self) -> None:
        x_values = [self.experience[query_name]["featurization"] for query_name in self.experience]
        y_values = [self.experience[query_name]["label"] for query_name in self.experience]
        query_names = list(self.experience.keys())
        #hs_lookup_dict = dict()
        #for i in range(0,64):
        #    hs_lookup_dict[i] = (1/64)*i
        #for j in range(len(y_values)):
        #    y_values[j] = hs_lookup_dict[y_values[j]]
        #print("Feature lengths")
        #for x in x_values:
        #    print(str(len(x) / 4))

        #x_ndarray = numpy.array(x_values)
        #x_tensor = tf.convert_to_tensor(x_values, dtype=tf.float64)
        #x_tensor = tf.expand_dims(x_tensor, axis=0)
        #print(x_ndarray.shape)

        #tf.reshape(x_ndarray, x_ndarray.shape)

        #x_values = numpy.array(x_values)
        x_values = numpy.array(x_values)
        y_values = np_utils.to_categorical(y_values)

        model = nn.get_uncompiled_model(x_values.shape)

        model.summary()
        #TODO: shouldn't the shape be (1012,164,1)?
        #TODO: train, test und val dataset

        batch_size = 16
        #train_dataset = tf.data.Dataset.from_tensor_slices((x_values, y_values))
        #train_dataset = train_dataset.shuffle(buffer_size=1024).batch(batch_size)

        model.compile(optimizer=keras.optimizers.SGD(), loss='categorical_crossentropy', metrics=keras.metrics.CategoricalAccuracy())

        history = model.fit(x_values, y_values, batch_size=64, epochs=100)


        #model = nn.get_uncompiled_model(train_dataset.shape)
        #loss = nn.CustomLoss()
        #optimizer = keras.optimizers.SGD(learning_rate=1e-3)

        #estimator = keras.wrappers.scikit_learn.KerasClassifier(build_fn=nn.get_compiled_model, epochs=10, batch_size=16, verbose=1)
        #kfold = sklearn.model_selection.KFold(n_splits=10, shuffle=True)
        #results = sklearn.model_selection.cross_val_score(estimator, x_values, y_values, cv=kfold)
        #print(results.mean()*100)

        #TODO: custom loss in a future project
        # epochs = 2
        # for epoch in range(epochs):
        #     # Iterate over the batches of the dataset.
        #     for step, (x_batch_train, y_batch_train) in enumerate(train_dataset):
        #         # Open a GradientTape to record the operations run
        #         # during the forward pass, which enables auto-differentiation.
        #         #x_batch_train = tf.reshape(x_batch_train, [batch_size,x_ndarray.shape[1], 1])
        #         querys = query_names[step*batch_size:(step+1)*batch_size]
        #         with tf.GradientTape() as tape:
        #             # Run the forward pass of the layer.
        #             # The operations that the layer applies
        #             # to its inputs are going to be recorded
        #             # on the GradientTape.
        #             logits = model(x_batch_train, training=True)  # Logits for this minibatch
        #
        #             loss.query_names = querys
        #             loss_value = loss.call(y_batch_train, logits)
        #         grads = tape.gradient(loss_value, model.trainable_weights)
        #         optimizer.apply_gradients(zip(grads, model.trainable_weights))

        # new models are not deployed right away since they might be subject of cooldown restrictions
        # unless no initial model is present
        if self.model is None:
            self.model = model
        else:
            self.new_model = model
        ###############################################################################################################
        # clf = GridSearchCV(estimator=GradientBoostingClassifier(random_state=self.seed), param_grid={
        #     "n_estimators": [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900,
        #                      1000],
        #     "max_depth": [1, 2, 3, 4, 5, 10, 20, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900,
        #                   1000]})
        # clf.fit(x_values,y_values)

        #model_estims = new_model.estimators_[0]
        #estims_list = list()
        #for estim in model_estims:
        #    estims_list.append(str(estim.tree_.max_depth))
        #with open("/Users/chrisgoerner/Documents/BA/FASTgres/results/depths.json", "a") as depths:
        #    depths.write(json.dumps(estims_list))
        # plot_tree(estim)
        # plt.show()

        return

    def predict(self, query_featurization: list[float]) -> int:
        # we look up our experience for convenient overlaps
        # -> this should be especially useful for learning to represent
        # can be commented out for true predictions for every query

        # for query_name in self.experience:
        #     exp_featurization = self.experience[query_name]["featurization"]
        #     if np.array_equal(exp_featurization, query_featurization):
        #         return int(self.experience[query_name]["label"])

        return int(self.model.predict(np.reshape(query_featurization, (1, -1)))[0])

    def move_critical_to_experience(self) -> float:
        labeling_time = 0.0
        for query_name in self.critical:
            self.experience[query_name]["featurization"] = deepcopy(self.critical[query_name]["featurization"])
            self.experience[query_name]["label"] = self.critical[query_name]["label"]
            self.experience[query_name]["time"] = self.critical[query_name]["time"]
            labeling_time += self.critical[query_name]["time"]
            # no influence on the performance, just for capturing info
            self.critical_queries.add(query_name)
        # all critical queries have been taken over to experience
        self.critical = u.tree()
        return labeling_time

    def run_observed_query(self, query_name: str, query_featurization: list[float], context_models) -> int:

        # first, check if we can deploy a new model for prediction
        if self.new_model is not None and self.cooldown <= 0:
            print("Deploying new model on context: {}".format(self.context))
            self.model = self.new_model
            self.new_model = None
            self.cooldown = 0

        prediction = self.predict(query_featurization)
        hint_set = HintSet(prediction)

        # second, check archive to speed up the simulated scenario
        try:
            result_time = self.archive[query_name][str(prediction)]
        except KeyError:
            print("Defaulting to pg evaluation, hint set: {} should be caught".format(prediction))
            # no archive info found -> manual eval in server | for client side eval we need all predictions
            result_time = u.evaluate_hinted_query(self.path, query_name, hint_set, self.db_string, self.timeout)
            # if learned path is given, this segment will later be saved
            self.archive[query_name][str(prediction)] = result_time

        # 2 scenarios: time, None may be possible here, archive time might be worse than the timeout!
        if result_time is None or result_time >= self.timeout:
            # the query is critical and should and possibly trigger retraining
            # same format as experience for easy handling
            print("Caught timeout")
            # at this point we already decide to return PG default as retraining does not influence this decision
            result_time = self.archive[query_name]["63"]

            if self.cooldown <= 0 and self.new_model is None:
                self.critical[query_name]["featurization"] = deepcopy(query_featurization)
                self.critical[query_name]["label"] = self.archive[query_name]["opt"]
                self.critical[query_name]["time"] = self.archive[query_name][str(self.archive[query_name]["opt"])]

                # we have capacity to train a new model, double check just in case
                # first we need to move any critical query to our experience
                # these queries decide on how long our cooldown will be
                # these four steps should always be taken when retraining
                labeling_time = self.move_critical_to_experience()
                self.train()
                self.update_timeout()
                self.cooldown += labeling_time
            else:
                # we still have a model that is being trained
                # -> we can additionally deduct the timeout for critical queries
                for c in context_models:
                    model = context_models[c]
                    if not isinstance(model, int):
                        model.cooldown -= self.timeout
                # self.cooldown -= self.timeout

        # At the end, we have to deduct our query runtime from the current cooldown
        # self.cooldown -= result_time
        for c in context_models:
            model = context_models[c]
            if not isinstance(model, int):
                model.cooldown -= result_time
        return prediction


def label_query(path, query, db_string):
    timeout = None
    best_hint = None
    query_entry = u.tree()
    for j in range(2 ** len(HintSet.operators)):
        j = (2 ** len(HintSet.operators) - 1) - j
        print("Evaluating Hint Set {}/ {}".format(j, (2 ** len(HintSet.operators)) - 1))
        print('Evaluating Query')
        hint_set = HintSet(j)
        query_hint_time = u.evaluate_hinted_query(path, query, hint_set, db_string, timeout)

        if query_hint_time is None:
            print('Timed out query')
            continue
        else:
            query_entry[query][j] = query_hint_time

            # update timeout
            if timeout is None or query_hint_time < timeout:
                timeout = query_hint_time
                best_hint = j

        print('Adjusted Timeout with Query: {}, Hint Set: {}, Time: {}'
              .format(query, u.int_to_binary(j), query_hint_time))
    query_entry[query]['opt'] = best_hint
    return query_entry


def load_label_dict(eval_dict):
    l_dict = dict()
    for key in eval_dict.keys():
        l_dict[key] = eval_dict[key]['opt']
    return l_dict


def get_query_labels(queries, label_dict):
    labels = list()
    for query in queries:
        labels.append([query, label_dict[query]])
    return labels


def load_features(feature_path: str) -> u.tree():
    # query -> table -> column -> values
    feature_dict = u.load_pickle(feature_path + "featurization.pkl")
    return feature_dict


def load_label_encoders(encoder_path):
    return u.load_pickle(encoder_path + "label_encoders.pkl")


def load_mm_dict(mm_path):
    return u.load_pickle(mm_path + "mm_dict.pkl")


def load_wildcard_dict(wildcard_path):
    return u.load_json(wildcard_path + "wildcard_dict.json")


def build_query_feature_dict(queries: list[str], feature_dict: dict, context: frozenset, d_type_dict) -> dict:
    features = dict()
    for query_name in queries:
        feature_vector = []
        for table in context:
            for column in d_type_dict[table]:
                entry = feature_dict[query_name][table][column]
                if entry:
                    feature_vector.extend(entry)
                else:
                    feature_vector.extend([0 for _ in range(4)])
        features[query_name] = feature_vector
    return features


def get_context_queries(queries, path, query_object_dict):
    query_context_dict = dict()
    for query_name in queries:
        # context = u.get_context(query_name, path)
        context = query_object_dict[query_name].context
        try:
            query_context_dict[context].add(query_name)
        except KeyError:
            query_context_dict[context] = {query_name}
    return query_context_dict


def get_from_merged_context(query: Query, merged_contexts):
    context = None
    for c in merged_contexts:
        if query.context in merged_contexts[c]:
            context = c
            break
    return context


def get_query_split(queries, args_test_queries):
    train_queries, test_queries = list(sorted(set(queries).difference(set(args_test_queries)))), \
                                  list(sorted(args_test_queries))
    # catch learning to represent
    if len(test_queries) == 0 or len(train_queries) == 0:
        return deepcopy(args_test_queries), deepcopy(args_test_queries)
    return train_queries, test_queries


def train_context_model(context_queries, train_queries, context, context_models, query_object_dict, db_string, mm_dict,
                        enc_dict, wc_dict, skipped_dict, d_type_dict, archive, seed, a_timeout, p_timeout, query_path,
                        estimators, estimator_depth, learning_rate, min_samples_split):
    print("Training Context {} / {}"
          .format(list(context_queries.keys()).index(context) + 1, len(context_queries.keys())))

    context_train_queries = list(sorted(set(context_queries[context]).intersection(set(train_queries))))
    if not context_train_queries:
        # No queries -> ignore
        return context_models, 0

    f_dict = dict()
    # avg_encoding_time = 0
    for query_name in context_train_queries:
        # query = Query(query_name, query_path)
        query = query_object_dict[query_name]
        f_d = featurize.build_feature_dict(query, db_string, mm_dict, enc_dict, wc_dict, set(), set(), skipped_dict)
        f_dict[query_name] = featurize.encode_query(context, f_d, d_type_dict)

    experience = u.tree()
    for query_name in context_train_queries:
        experience[query_name]["featurization"] = f_dict[query_name]
        experience[query_name]["label"] = archive[query_name]["opt"]
        experience[query_name]["time"] = archive[query_name][str(archive[query_name]["opt"])]

    # catch one elementary labels
    label_uniques = np.unique([experience[query_name]["label"] for query_name in context_train_queries])
    if len(label_uniques) == 1:
        context_models[context] = int(label_uniques[0])
        train_time = 0
    else:
        observer = QueryObserver(seed, context, archive, experience, a_timeout, p_timeout, query_path, db_string,
                                 estimators, estimator_depth, learning_rate, min_samples_split)
        t0 = time.time()
        observer.train()
        train_time = time.time() - t0
        context_models[context] = observer
        # print(observer)
    return context_models, train_time


def test_query(query_name, merged_contexts, db_string, mm_dict, enc_dict, wc_dict, unhandled_op, unhandled_type,
               skipped_dict, query_object_dict, context_models, prediction_dict, d_type_dict, use_cqd):
    t0 = time.time()
    # query_obj = Query(query_name, query_path)
    query_obj = query_object_dict[query_name]
    context = get_from_merged_context(query_obj, merged_contexts)

    # encode test query
    feature_dict = featurize.build_feature_dict(query_obj, db_string, mm_dict, enc_dict, wc_dict, unhandled_op,
                                                unhandled_type, skipped_dict)
    encoded_test_query = encode_query(context, feature_dict, d_type_dict)

    try:
        observer = context_models[context]
    except:
        # incoming context was not seen before, we default
        prediction_dict[query_name] = 63
        return prediction_dict, time.time() - t0
    if isinstance(observer, int):
        prediction = observer
    else:
        if use_cqd:
            prediction = observer.run_observed_query(query_name, encoded_test_query, context_models)
        else:
            prediction = observer.predict(encoded_test_query)
    forward_time = time.time() - t0
    prediction_dict[query_name] = prediction
    return prediction_dict, forward_time


def evaluate_workload(query_path, seed, archive, enc_dict, mm_dict, wc_dict, p_timeout, a_timeout, db_string,
                      skipped_dict, use_context, args_test_queries: list, query_object_dict: dict,
                      use_cqd: bool, estimators: int, estimator_depth: int, learning_rate, min_samples_split):
    # load queries
    queries = u.get_queries(query_path)
    # predetermine context
    context_queries = get_context_queries(queries, query_path, query_object_dict)
    # merge if needed
    if not use_context:
        context_queries, merged_contexts = merge_context_queries(context_queries)
    else:
        merged_contexts = {key: {key} for key in context_queries}

    # split queries
    train_queries, test_queries = get_query_split(queries, args_test_queries)

    # init context model dict and build db meta data
    context_models = dict()
    d_type_dict = u.build_db_type_dict(db_string)

    ###################################################################################################################

    print("Training/Testing/All Queries: {} / {} / {}".format(len(train_queries), len(test_queries), len(queries)))
    print("Training contexts")
    training_time = dict()
    for context in alive_it(context_queries):
        context_models, train_time = train_context_model(context_queries, train_queries, context, context_models,
                                                         query_object_dict, db_string, mm_dict, enc_dict, wc_dict,
                                                         skipped_dict, d_type_dict, archive, seed, a_timeout,
                                                         p_timeout, query_path, estimators, estimator_depth, learning_rate, min_samples_split)
        training_time[context] = train_time
    print("Training phase done")

    ###################################################################################################################

    # [print(context_models[context]) for context in context_models]

    # table_column_dict = build_table_column_dict(queries, query_path)
    init_predictions = dict()
    final_predictions = dict()
    forward_pass_time = dict()
    unhandled_op, unhandled_type = [set() for _ in range(2)]
    for query_name in alive_it(test_queries):
        init_predictions, forward_time = test_query(query_name, merged_contexts, db_string, mm_dict, enc_dict, wc_dict,
                                                    unhandled_op, unhandled_type, skipped_dict, query_object_dict,
                                                    context_models, init_predictions, d_type_dict, use_cqd)
        forward_pass_time[query_name] = forward_time

    ###################################################################################################################

    if use_cqd:
        # capture critical queries
        critical_queries = dict()
        for context in context_models:
            model = context_models[context]
            if not isinstance(model, int):
                critical_queries[model.context] = list(sorted(model.critical_queries))

        for query_name in alive_it(test_queries):
            # query_obj = Query(query_name, query_path)
            query_obj = query_object_dict[query_name]
            context = get_from_merged_context(query_obj, merged_contexts)
            try:
                observer = context_models[context]
            except:
                # unseen queries are again handled by PG
                final_predictions[query_name] = 63
                continue

            feature_dict = featurize.build_feature_dict(query_obj, db_string, mm_dict, enc_dict, wc_dict, unhandled_op,
                                                        unhandled_type, skipped_dict)
            encoded_test_query = encode_query(context, feature_dict, d_type_dict)

            if isinstance(observer, int):
                prediction = observer
            else:
                prediction = observer.predict(encoded_test_query)
            final_predictions[query_name] = prediction
    else:
        final_predictions = None
        critical_queries = None

    return init_predictions, final_predictions, training_time, forward_pass_time, critical_queries

def main(params):
    learning_rate, estimators, estimatordepth, min_samples_split = params
    parser = argparse.ArgumentParser(description="Fastgres Evaluation")
    parser.add_argument("-queries", default="/Users/chrisgoerner/Documents/BA/FASTgres/queries/stack/all/",
                        help="Query Path to evaluate")
    parser.add_argument("-s", "--seed", default=29, help="Random seed to use for splitting.")
    parser.add_argument("-db", "--database", default="stack", help="Database the given queries should run on. "
                                                                   "Shortcuts imdb, stack exist. "
                                                                   "Databases in the Psycopg2 db string input are "
                                                                   "possible too.")
    parser.add_argument("-a", "--archive", default="/Users/chrisgoerner/Documents/BA/FASTgres/labels/stack_eval_dict_ax1_fixed.json",
                        help="Path to an existing query evaluation dictionary "
                             "If no dictionary is provided, queries will be "
                             "evaluated on-line.")
    parser.add_argument("-dbip", "--databaseinfopath",
                        default="/Users/chrisgoerner/Documents/BA/FASTgres/db_info/stack/",
                        help="Path to database info in which label "
                             "encoders, min-max dictionaries, and wildcard"
                             " dictionaries are located.")
    parser.add_argument("-pt", "--percentagetimeout", default=99, help="Percentage timeout to use for CQD.")
    parser.add_argument("-at", "--absolutetimeout", default=1, help="Absolute timeout to use for CQD.")
    parser.add_argument("-sd", "--savedir", default="/Users/chrisgoerner/Documents/BA/FASTgres/results/50/dummy/",
                        help="Save directory in which to save evaluation to.")
    parser.add_argument("-uc", "--usecontext", default="True", help="Declare usage of context or roll up the workload.")
    parser.add_argument("-bp", "--baoprediction", default=None, help="Path to bao predictions to use as queries."
                                                                     "If provided, the standard split will be "
                                                                     "overwritten.")
    parser.add_argument("-qo", "--queryobjects",
                        default="/Users/chrisgoerner/Documents/BA/FASTgres/evaluation/stack/query_objects.pkl",
                        help="Path to query object .pkl to shorten eval.")
    parser.add_argument("-sp", "--splitpath",
                        default="/Users/chrisgoerner/Documents/BA/FASTgres/evaluation/stack/14.6/splits/50/run_0.json",
                        help="Path to split to use (json, 'train', 'test'). "
                             "Overwrites bp.")
    parser.add_argument("-cqd", "--querydetection", default="False", help="Whether to use CQD or not. "
                                                                          "If False, -fp will be ignored. "
                                                                          "Default: True")
    parser.add_argument("-l", "--learn", default=None, help="Path to update an existing archive or not. "
                                                            "Be sure to only use this option on the hardware your "
                                                            "archive was generated on. "
                                                            "Defaults to None.")
    parser.add_argument("-est", "--estimators", default=100, help="Numbers of estimators to use. "
                                                                  "Defaults to 100.")
    parser.add_argument("-ed", "--estimatordepth", default=1, help="Max depth of a single estimator. "
                                                                      "Defaults to 1000.")
    args = parser.parse_args()
    query_path = args.queries

    if not os.path.exists(query_path):
        raise ValueError("Given query path does not exist.")

    args_seed = args.seed
    if not isinstance(args_seed, int):
        raise ValueError("Given seed was not an integer.")

    args_db = "stack"
    if args_db == "stack":
        args_db = u.PG_STACK_OVERFLOW

    args_archive_path = args.archive
    if args_archive_path is None:
        raise ValueError("No archive path provided.")
    args_archive = u.load_json(args_archive_path)

    args_dbinfo_path = args.databaseinfopath
    if args_dbinfo_path is None:
        raise ValueError("No database information path provided.")

    args_save_path = args.savedir
    if args_save_path is None:
        raise ValueError("No save path provided")

    args_use_context = args.usecontext
    if args_use_context not in ["True", "False"]:
        raise ValueError("Invalid context option -uc provided.")
    args_use_context = True if args_use_context == "True" else False

    args_query_objects_path = args.queryobjects
    if args_query_objects_path is None:
        raise ValueError("Query Objects -qo not provided")
    args_query_objects = u.load_pickle(args_query_objects_path)

    # table -> column -> encoder
    args_label_encoders = load_label_encoders(args_dbinfo_path)
    # table -> column -> [min, max]
    args_mm_dict = load_mm_dict(args_dbinfo_path)
    # table -> max card | column -> filter -> card
    args_wildcard_dict = load_wildcard_dict(args_dbinfo_path)
    # table -> columns | rows
    if os.path.exists(args_dbinfo_path + "skipped_table_columns_stack.json"):
        args_skipped_dict = u.load_json(args_dbinfo_path + "skipped_table_columns_stack.json")
    else:
        print("No skipped column dict found, skipping")
        args_skipped_dict = dict()

    args_p_timeout = int(args.percentagetimeout)
    args_a_timeout = float(args.absolutetimeout)

    args_bao_pred = args.baoprediction
    args_split_path = args.splitpath
    if args_bao_pred is not None and os.path.exists(args_bao_pred):
        args_bao_test_queries = list(u.load_json(args_bao_pred).keys())
        args_test_queries = args_bao_test_queries
    elif args_split_path is not None and os.path.exists(args_split_path):
        args_split_dict = u.load_json(args_split_path)
        args_split_train, args_split_test = list(args_split_dict["train"]), list(args_split_dict["test"])
        args_test_queries = args_split_test
    else:
        raise ValueError("Either a BAO prediction or a query split dictionary must be provided for comparison.")

    args_cqd = args.querydetection
    if args_cqd not in ["True", "False"]:
        raise ValueError("Invalid evaluation option -cqd provided.")
    args_cqd = True if args_cqd == "True" else False

    args_learn_path = args.learn
    args_estimators = int(estimators)
    args_estimator_depth = int(estimatordepth)
    args_learning_rate = float(learning_rate)
    args_min_samples_split = int(min_samples_split)

    print("Using absolute/percentage based timeout: {}s / {}%".format(args_a_timeout, args_p_timeout))
    #"s" + str(min_samples_split) +
    #################################################################
    init_predictions, final_predictions, training_time, forward_pass_time, critical_queries \
        = evaluate_workload(query_path, args_seed, args_archive, args_label_encoders, args_mm_dict, args_wildcard_dict,
                            args_p_timeout, args_a_timeout, args_db, args_skipped_dict, args_use_context,
                            args_test_queries, args_query_objects, args_cqd, args_estimators, args_estimator_depth, args_learning_rate, args_min_samples_split)
    u.save_json(init_predictions, args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "initial_predictions.json")
    u.save_pickle(training_time, args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "training_times.pkl")
    u.save_json(forward_pass_time, args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "forward_pass_times.json")
    predictions_path = args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "initial_predictions.json"
    if args_cqd:
        u.save_json(final_predictions, args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "final_predictions.json")
        u.save_pickle(critical_queries, args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "critical_queries.pkl")
        predictions_path = args_save_path + "s" + str(min_samples_split) + "l" + str(learning_rate) + "e" + str(estimators) + "d" + str(estimatordepth) + "final_predictions.json"
    if args_learn_path is not None:
        u.save_json(args_archive, args_learn_path)
    return speedup(args_archive_path, predictions_path)


if __name__ == "__main__":
    main([0.1,100,100,2])

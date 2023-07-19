import json


def speedup(labels_path, predictions_path):
    # f.ex.:
    # labels_path = "/Users/chrisgoerner/Documents/BA/FASTgres/labels/stack_eval_dict_ax1_fixed.json"
    # predictions_path = "/Users/chrisgoerner/Documents/BA/FASTgres/evaluation/stack/initial_predictions.json"

    with open(labels_path) as labels:
        with open(predictions_path) as predictions:
            predictions_dict = json.load(predictions)
            labels_dict = json.load(labels)
            # if there is no prediction for the labeled query
            undefined = []
            # if the predicted hint set is not in labels
            mismatch = []
            exact_match = []
            for key in labels_dict:
                if key in predictions_dict:
                    opt = int(labels_dict[key]["opt"])
                    if opt is predictions_dict[key]:
                        exact_match.append(key)
                    else:
                        mismatch.append(key)
                else:
                    undefined.append(key)
            # average PG default execution time and average speedup
            # execution_time = {query_name : [pg_default_execution_time, optimal_hs_execution_time, predicted_hs_execution_time]}
            execution_time = dict()
            not_here = list()
            for key in labels_dict:
                if key in predictions_dict:
                    pg_default_execution_time = [labels_dict[key]["63"]]
                    execution_time[key] = pg_default_execution_time
                    opt = str(labels_dict[key]["opt"])
                    optimal_hs_execution_time = labels_dict[key][opt]
                    execution_time[key].append(optimal_hs_execution_time)
                    predicted_hs = str(predictions_dict[key])
                    if predicted_hs in labels_dict[key].keys():
                        predicted_hs_execution_time = labels_dict[key][predicted_hs]
                        execution_time[key].append(predicted_hs_execution_time)
                    else:
                        del execution_time[key]
                        not_here.append(key)
            predictions.close()
        labels.close()
    print(len(not_here))
    pg_list = [execution_time[x][0] for x in execution_time.keys()]
    speedup_list = [execution_time[x][2] for x in execution_time.keys()]
    average_speedup = sum(pg_list) / sum(speedup_list)
    #zip_list = [i / j for i, j in zip(pg_list, speedup_list)]
    #average_speedup = sum(zip_list) / len(zip_list)
    # print("Total: " + str(len(labels_dict)))
    # print("Exact match: " + str(len(exact_match)))
    # print("Mismatch: " + str(len(mismatch)))
    # print("Used for Training: " + str(len(undefined)))
    # print("Average PG Default Speed: " + str(average_pg_time))
    # print("Average Predicted HS Speed: " + str(average_speedup_time))
    # print("Average FG Speedup: " + str(average_speedup))

    return average_speedup

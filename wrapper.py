import evaluate_queries as eval
from joblib import Parallel, delayed
import os
import numpy as np
import time

def gridsearch(split_path, savedir):
    # for grid search:
    learning_rate = np.logspace(start=-5,stop=0.0,num=12) #l
    n_estimators = [1, 2, 5, 10, 20, 50, 100, 200, 500]  # e
    max_depth = [1, 2, 5, 10, 20, 50, 100, 10000]  # d
    # for baseline:
    #learning_rate = [0.1]
    # n_estimators = [100]
    # max_depth = [1000]
    # for 10% split optimization results propagation:
    # learning_rate = [0.0006579332246575682]
    # n_estimators = [200]
    #n_estimators = [100]
    # max_depth = [5]
    subsample = [1.0] #s
    criterion = ['friedman_mse'] #c
    min_samples_split = [2] #mins
    min_samples_leaf = [1] #minl
    min_weight_fraction_leaf = [0] #minwl
    min_impurity_decrease = [0] #mini
    max_features = [None] #mf
    max_leaf_nodes = [None] #ml
    warm_start = [False] #ws
    #validation_fraction = []
    #ccp_alpha = []

    Parallel(n_jobs=-1)(delayed(eval.main)(sp,sd,l,e,s,c,mins,minl,minwl,d,mini,mf,ml,ws) for ws in warm_start for ml in max_leaf_nodes for mf in max_features for mini in min_impurity_decrease for d in max_depth for minwl in min_weight_fraction_leaf for minl in min_samples_leaf for mins in min_samples_split for c in criterion for s in subsample for e in n_estimators for l in learning_rate for sd in [savedir] for sp in [split_path])
    return


def listnotinstr(list, string):
    for l in list:
        if str(l) in string:
            return False
    return True

if __name__ == "__main__":
    # insert split path and save directory here
    splits_path = "/home/goerner/FASTgres/evaluation/stack/14.6/splits/90/"
    savedir = "/home/goerner/FASTgres/results/90/"
    no_run_list = [0, 5, 6, 7, 8, 9]
    start = time.process_time()
    for file in sorted(list(os.listdir(splits_path))):
        if ("c_run" not in file) and ("run" in file) and listnotinstr(no_run_list, file):
            if not os.path.exists(savedir + file.replace('.json','') + 'logscale'):
                os.mkdir(savedir + file.replace('.json','') + 'logscale')
            gridsearch(splits_path + file, savedir + file.replace('.json','') + 'logscale' + '/')
    print(time.process_time() - start)
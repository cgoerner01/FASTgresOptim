# FASTgresOptim

This repository contains files continuing [FASTgres](https://github.com/JeromeThiessat/FASTgres), originally created by J. Thiessat for their Master's thesis. This project represents an extension of their original work as part of my own Bachelor's thesis at the Chair of Databases, Faculty of Computer Science at TU Dresden. To ensure the functionality of these files, refer to Thiessat's repository.

evaluate_queries.py: Was modified to support grid search. The files created at the end of training/testing state the hyperparameters applied for each run in name of the file.

wrapper.py: To run the grid search. Joblib.Parallel class with n_jobs=-1 makes use of all cores, adjust if necessary. Enter the split path and save directory. The results from my thesis can be recreated using the configurations for learning_rate, max_depth and n_estimators. For the baseline, grid search and 10% robustness test, these values are given in the script (potentially commented out). The other hyperparameter are set to their default value.

fill_eval_dictionary.py: Modified to automatically re-label all prediction files of a grid search run by entering the save directory.

evaluate_queries_nn.py: Integration of simple neural network into FASTgres using tensorflow. Please note that this evaluation script is not fully functional and will run into errors before fully running through. Investigating the effects of the neural network is recommended by manually iterating through the QueryObserver's train method.

nn.py: Definition of the neural network called in evaluate_queries_nn.py.

score.py: Evaluates the speedup for a given prediction file and archive.

grid_search_graph.py: Creates a graph from grid search predictions. Directories created by evaluate_queries.py serve as input. The results_paths variable can take a list of grid search prediction save directories with the same grid points. At the end of computing all speedup factors through score.py, the hyperparameter configuration that achieved the highest speedup given the prediction file(s) is printed to the console. Attention! Giving a list as results_paths computes the average speedup over all input directories.



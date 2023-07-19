import os
import score
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from matplotlib import cm
import matplotlib
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from tqdm import tqdm
import re
import collections

def plotled(results_path, labels_path):
    # hyperparameter code -> code in filename, like "l" for "learning_rate"
    # from back to front, f.ex. s2l0.01e1d6initial_predictions -> ["d", "e", "l", "s"]
    vals = dict()
    for res in results_paths:
        for file in tqdm(os.listdir(res)):
            if file.endswith("initial_predictions.json"):
                filex = file.replace("initial_predictions.json", "")
                re_l = re.compile(r"l\d*.\d*(e-\d+)*")
                re_e = re.compile(r"e\d*s")
                re_d = re.compile(r"d\d*mini")

                l = re_l.search(filex).group().replace('l','')
                e = re_e.search(filex).group().replace('e','').replace('s','')
                d = re_d.search(filex).group().replace('d','').replace('mini','')

                filex = [e, d, l]
                filex = tuple(filex)
                # estimators.append(filex[0])
                # estimatordepth.append(filex[1])
                # speedup.append(score.speedup("/Users/chrisgoerner/Documents/BA/FASTgres/labels/stack_eval_dict_ax1_fixed.json", results_path + file))
                if filex not in vals:
                    vals[filex] = []
                vals[filex].append(score.speedup(labels_path, res + file))

    # averaging
    for k in vals.keys():
        vals[k] = sum(vals[k]) / len(vals[k])

    best = ()
    # print best configuration
    for k in vals.keys():
        if vals[k] == max(vals.values()):
            print(str(k) + ": " + str(vals[k]))
            best = vals[k]




    #get all possible values of column and row
    row = sorted(list(set([int(k[0]) for k in vals.keys()])))
    col = sorted(list(set([int(k[1]) for k in vals.keys()])))

    idx = 1
    plt.rcParams.update({'font.size': 6})
    fig = plt.figure(figsize=(12,8))
    for l in range(len(col)):
        for s in range(len(row)):
            learning_rates = [float(k[2]) for k in vals.keys() if int(k[0]) == row[s] and int(k[1]) == col[l]]
            speedups = [vals[tuple(k)] for k in vals.keys() if int(k[0]) == row[s] and int(k[1]) == col[l]]

            res = dict(zip(learning_rates,speedups))
            od = collections.OrderedDict(sorted(res.items()))
            res = dict(od)
            learning_rates = list(res.keys())
            speedups = list(res.values())
            #lin1 = np.linspace(min(estimators), max(estimators), len(set(estimators)))
            #lin2 = np.linspace(min(estimatordepths), max(estimatordepths), len(set(estimatordepths)))

            ax = fig.add_subplot(len(col), len(row), idx)
            pad = 5
            #if s == 0:
            #    ax.annotate("learning rate: " + str(learning_rates[l]), xy=(0, 0.5), xytext=(-ax.yaxis.labelpad - pad, 0),
            #                xycoords=ax.yaxis.label, textcoords='offset points',
            #                size='large', ha='right', va='center')
            if s == 0:
                ax.annotate("depth: " + str(col[l]), xy=(-0.4, 0.5), xytext=(0, pad),
                            xycoords="axes fraction", textcoords='offset points',
                            size='large', ha='right', va='center')
            if l == 0:
                ax.annotate("estimators: " + str(row[s]), xy=(0.5, 1), xytext=(0, pad),
                            xycoords='axes fraction', textcoords='offset points',
                            size='large', ha='center', va='baseline')
            #ax.set_xlabel("nestimators")
            #ax.set_ylabel("max_depth")
            #ax.set_xticks([1, 100, 1000])
            #ax.set_yticks([1, 10, 30])
            #surf = ax.plot_surface(linx, liny, speedupx, cmap=cm.coolwarm)
            ax.plot(learning_rates, speedups, color='#009e73')
            #fig.colorbar(surf)
            idx += 1
    #fig.subplots_adjust(left=0.15, top=0.95)
    fig.tight_layout(h_pad=1)
    plt.savefig("70percentgridsearch.jpg", dpi=400)
    plt.show()
    return

if __name__ == "__main__":
    #dims = ["d", "e", "l", "ms"]
    #relative Pfade nehmen
    #results_paths = ["/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_0logscale/","/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_1logscale/","/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_2logscale/","/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_3logscale/","/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_4logscale/"]
    results_paths = ["/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_1baseline/","/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_1baseline/"]
    #results_paths = ["/Users/chrisgoerner/Documents/BA/FASTgres/results/70/run_4baseline/"]
    #results_paths = ["/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_0generality/","/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_1generality/","/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_2generality/","/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_3generality/","/Users/chrisgoerner/Documents/BA/FASTgres/results/90/run_4generality/"]
    labels_path = "/Users/chrisgoerner/Documents/BA/FASTgres/labels/17072023_2052.json"
    plotled(results_paths, labels_path)

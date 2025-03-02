# implementation of the PERT methode/algorithm in python by SEK171

# to run please install the necessary packages:
# graphviz
# tkinter
# customtkinter


# ------------- still under developement, a lot of bugs ----------------------


# a library used to graph dot plots/diagrams
import graphviz
from graphviz import Digraph

import copy
import random

# library used for graphical interface
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import subprocess

# definition du graphe
X = {}
U = {}


# create the precedents dictionary
def UtoUi(U):
    Ui = {node: set() for node in U}

    for x, suivants in U.items():
        for suivant in suivants:
            if suivant not in Ui:
                Ui[suivant] = set()
            Ui[suivant].add(x)

    return Ui


# define the classes
def Niveaux(precedents):
    niveaux = {}
    niveau_actuel = 0

    # l'orsqu'on a des noeus a processer
    while precedents:
        # list des noueds
        noeuds = []

        # loop through all the points
        for n in list(precedents.keys()):
            # si le point n'admet pas des precedents on peut affecter un niveau
            if not precedents[n]:
                noeuds.append(n)

        # si on a rien noeuds we break
        if not noeuds:
            break

        # pour chack noeud de cette niveau on affect son niveau
        for n in noeuds:
            niveaux[n] = niveau_actuel
            # supprime de list des precedents
            del precedents[n]  # la sommet
            for pas_n in precedents:  # pour chaque autre sommet
                if n in precedents[pas_n]:  # si il admet cette point comme precedent
                    precedents[pas_n].remove(n)  # supprime

        # niveu suivant
        niveau_actuel += 1

    return niveaux


# plot the graphe
def pert_graph(X, Ui, NV, C):
    # define the dot diagram
    dot = Digraph("Graphe", format='svg')
    # basically the width of the graph
    dot.body.append('\tgraph [nodesep=0.8];\n')
    # the shape of the nodes of the graph
    dot.body.append('\tnode [shape=circle];\n')

    # a copy of C
    Cs = copy.deepcopy(C)

    # define each node (sommets)
    index = 1  # label of the node
    for x in Ui:
        if "redun" not in x:
            dot.node(x, label=str(index))
            index += 1
        else:
            Cs[NV[x.replace("_redundant", "")]].remove(x.replace("_redundant", ""))

    # define each edge (arcs)
    for y in Ui:
        if "redun" not in y:
            for x in Ui[y]:
                # check if it is a virtual node
                if "dash" in x:
                    dot.edge(x.replace("_dash", ""), y, label=f"{x.replace("_dash", "")} (0)", style="dashed")
                elif "redun" in x:
                    dot.edge(list(Ui[x])[0], y, label=f"{x.replace("_redundant", "")} ({str(X[y])})")
                else:
                    # add the connection and it's distance
                    dot.edge(x, y, label=f"{y} ({str(X[y])})")

    # tracer les niveau de generations
    for i in Cs:
        for x in Cs[i]:
            dot.body.append('{ rank = same; ' + '; '.join(Cs[i]) + '}\n')

            # return the graph
    return dot


# define the function for reducing the redundant parts
def transitive_reduction(graph, graph_precedents):
    # create the copy
    reduced_graph = copy.deepcopy(graph_precedents)

    # loop through all nodes we have
    for node in graph_precedents:
        # loop through all sub nodes aka children of the parent node
        for child in graph_precedents[node.replace("_dash", "")]:
            # if a child node is a parent of any other node in this list, delete it
            for parent_child in graph[child.replace("_dash", "")]:  # loop through the children of every child
                # if it is part of the precedents
                if parent_child in graph_precedents[node.replace("_dash", "")]:
                    # delete it if it exists (haven't been delted before)
                    try:
                        reduced_graph[node].remove(child)
                    except:
                        pass

    # return the reduced graph
    return reduced_graph


# remove duplicate virtual or real nodes (les remarques)
def remove_duplicates(graph, graph_precedents, NV):
    # we will need to remove connections for tasks with more than one source
    final_graph = copy.deepcopy(graph_precedents)

    # loop through all nodes we have
    for node in graph_precedents:
        # check if a node has more than 2 sources
        if len(list(final_graph[node])) > 1:
            while len(list(final_graph[node])) > 1:
                # choose one to remove (lowest rank else random choice)
                options = list(final_graph[node])
                if NV[options[0]] > NV[options[1]]:
                    choice = options[1]
                elif NV[options[0]] < NV[options[1]]:
                    choice = options[0]
                else:
                    choice = options[random.randint(0, 1)]

                # remove one of the connections
                final_graph[node].remove(choice)
                options.remove(choice)

                # check the edge case if it is redundent
                if list(final_graph[choice])[0] not in final_graph[options[0]]:
                    final_graph[options[0]].add(f"{choice}_redundant")
                    final_graph[f"{choice}_redundant"] = set(final_graph[choice])
                    final_graph.pop(choice)


                else:
                    # make a virtual connection
                    final_graph[options[0]].add(f"{choice}_dash")

    return final_graph


# calcule du temp plus tot
def earliest_time(X, Ui):
    earliest = {}
    # temp de debut (0)
    earliest["DEBUT"] = X["DEBUT"]

    # Loop through tasks
    for y in X:
        if y != "DEBUT":
            # add the task length to the length of the maximum path before it
            temp = max(earliest[x] for x in Ui[y]) if Ui[y] else 0
            earliest[y] = temp + X[y]

    return earliest


# temps plus tard
def latest_time(X, U, earliest, C):
    latest = {}
    # temp du fin
    latest[C[len(C) - 1][0]] = earliest[C[len(C) - 1][0]]

    # loop through tasks in reverse order
    for x in reversed(list(X.keys())):
        if x != "L":
            # get the minimum of the
            latest[x] = min(earliest[y] - X[y] for y in U[x]) if U[x] else earliest[x]

    return latest


# final graph of pert numbered
def final_pert(source, Ui, earliest, latest):
    temp = source

    for x in Ui:
        index = temp.find(f"{x} [label=") + len(f"{x} [label=")
        temp = list(temp)
        if temp[index + 1] != "]":
            number = temp[index] + temp[index + 1]
        else:
            number = temp[index]
        temp = "".join(temp)
        temp = temp.replace(f"{x} [label={number}", f'{x} [label="{earliest[x]} | {latest[x]}\\n{number}"', 1)

    graphe = graphviz.Source(temp, filename="Graphe", format="png")

    return graphe


# create the pert graph
def compute_graph(X, U):
    Ui = UtoUi(U)

    precedents = copy.deepcopy(Ui)  # copy of precedents
    NV = Niveaux(precedents)  # calc les niveaux
    C = {}  # la list (dictionnaire) des niveaux
    # inverser les elemenets et valeurs de NV et mettre en lists pour l'existence de plusieurs element de meme niveau
    for key, value in NV.items():
        C.setdefault(value, []).append(key)

    # add the starting node and it's connections
    X = {"DEBUT": 0, **X}
    U = {"DEBUT": set(C[0]), **U}

    # recompute with the results after update
    Ui = UtoUi(U)

    precedents = copy.deepcopy(Ui)  # copy of precedents
    NV = Niveaux(precedents)  # calc les niveaux
    C = {}  # la list (dictionnaire) des niveaux
    # inverser les elemenets et valeurs de NV et mettre en lists pour l'existence de plusieurs element de meme niveau
    for key, value in NV.items():
        C.setdefault(value, []).append(key)

    reduced = transitive_reduction(U, Ui)
    final = remove_duplicates(U, reduced, NV)

    earliest = earliest_time(X, Ui)
    latest = latest_time(X, U, earliest, C)

    final_graph = pert_graph(X, final, NV, C)
    pert = final_pert(final_graph.source, Ui, earliest, latest)
    pert.render()


################################## graphical display #####################################

# diplay the pert graph
def display_image(path):
    subprocess.run(["start", path], shell=True)


# on click submit
def on_submit(tasks):
    global X, U

    for i, row in enumerate(tasks):
        task = row[0].get()
        duration = row[1].get()
        suivants = row[2].get()

        if not task or not duration:
            messagebox.showerror("Error", "Remplir toot les champs.")
            return

        try:
            duration = int(duration)
        except:
            messagebox.showerror("Error", f"Duration de la tach {task} doit etre numerique.")
            return

        if suivants:
            list_suivants = {x.strip() for x in suivants.split(",") if x.strip()}
        else:
            list_suivants = {}

        X[task] = duration
        U[task] = list_suivants

    compute_graph(X, U)

    display_image("Graphe.png")

    messagebox.showinfo("Success", "formule rempli.")

    clear_all_rows(tasks)


# clear all form rows
def clear_all_rows(tasks):
    for task in tasks:
        for field in task:
            field.delete(0, tk.END)
    tasks.clear()


# add a task to the form
def add_task_row(tasks):
    row = []
    # tasks and their labels
    task_label = ctk.CTkLabel(frame, text="Tache:")
    task_label.grid(row=len(tasks), column=0, padx=10, pady=5, sticky="e")
    task_window = ctk.CTkEntry(frame)
    task_window.grid(row=len(tasks), column=1, padx=10, pady=5)
    row.append(task_window)

    # durations
    duration_label = ctk.CTkLabel(frame, text="Duration:")
    duration_label.grid(row=len(tasks), column=2, padx=10, pady=5, sticky="e")
    duration_window = ctk.CTkEntry(frame)
    duration_window.grid(row=len(tasks), column=3, padx=10, pady=5)
    row.append(duration_window)

    # nexts
    next_label = ctk.CTkLabel(frame, text="Suivaints:")
    next_label.grid(row=len(tasks), column=4, padx=10, pady=5, sticky="e")
    next_window = ctk.CTkEntry(frame)
    next_window.grid(row=len(tasks), column=5, padx=10, pady=5)
    row.append(next_window)

    tasks.append(row)


# generate all rows on the window
def generate_rows(tasks, number_tasks):
    clear_all_rows(tasks)

    add_task_row(tasks)

    for _ in range(number_tasks - 1):
        add_task_row(tasks)


# create the wrapper for the window
root = ctk.CTk()
root.title("PERT")
root.geometry(f"{str(1920 / 2)}x{str(1080 / 2)}")

ctk.set_appearance_mode("dark")  # dark mode theme

# create the frame for the root app
frame = ctk.CTkFrame(root)
frame.pack(padx=20, pady=20, fill="both", expand=True)

header_frame = ctk.CTkFrame(root)
header_frame.pack(pady=20, fill="x")
header_label = ctk.CTkLabel(header_frame, text="PERT", font=("Roboto", 20, "bold"))
header_label.pack(pady=5)

tasks = []

task_label_count = ctk.CTkLabel(root, text="Entere le nombre des taches", font=("Roboto", 14))
task_label_count.pack(pady=10)
task_window_count = ctk.CTkEntry(root, font=("Roboto", 12))
task_window_count.pack(pady=5)

generate_button = ctk.CTkButton(root, text="Generer les taches",
                                command=lambda: generate_rows(tasks, int(task_window_count.get())))
generate_button.pack(pady=10)

submit_button = ctk.CTkButton(root, text="Submit", command=lambda: on_submit(tasks), width=15, corner_radius=12)
submit_button.pack(pady=20)

# execute
root.mainloop()

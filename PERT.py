# implementation of the PERT methode/algorithm in python by SEK171

# to run please install graphviz

import graphviz
from graphviz import Digraph
import copy
import subprocess

# ── helpers ─────────────────────────────────────────────────────────────────

def UtoUi(U):
    """Build predecessor dict from successor dict."""
    Ui = {node: set() for node in U}
    for x, suivants in U.items():
        for s in suivants:
            Ui.setdefault(s, set()).add(x)
    return Ui


def Niveaux(Ui):
    """Assign topological levels to nodes."""
    precedents = {n: set(p) for n, p in Ui.items()}
    niveaux, niveau = {}, 0
    while precedents:
        ready = [n for n, p in precedents.items() if not p]
        if not ready:
            break
        for n in ready:
            niveaux[n] = niveau
            del precedents[n]
            for other in precedents:
                precedents[other].discard(n)
        niveau += 1
    return niveaux


def topological_sort(U):
    """Kahn's algorithm: deterministic (ties broken alphabetically)."""
    in_deg = {n: 0 for n in U}
    for n in U:
        for s in U[n]:
            in_deg[s] = in_deg.get(s, 0) + 1

    queue = sorted(n for n, d in in_deg.items() if d == 0)
    order = []
    while queue:
        n = queue.pop(0)
        order.append(n)
        for s in sorted(U.get(n, [])):
            in_deg[s] -= 1
            if in_deg[s] == 0:
                queue.append(s)
                queue.sort()
    return order


# ── graph reduction ──────────────────────────────────────────────────────────

def transitive_reduction(graph, graph_precedents):
    reduced = copy.deepcopy(graph_precedents)
    for node in graph_precedents:
        base_node = node.replace("_dash", "")
        for child in list(graph_precedents.get(base_node, [])):
            for parent_child in graph.get(child.replace("_dash", ""), set()):
                if parent_child in graph_precedents.get(base_node, set()):
                    try:
                        reduced[node].remove(child)
                    except (KeyError, ValueError):
                        pass
    return reduced


def remove_duplicates(graph, graph_precedents, NV):
    """Ensure each node has at most one direct predecessor."""
    final_graph = copy.deepcopy(graph_precedents)

    for node in list(graph_precedents.keys()):
        while len(final_graph.get(node, set())) > 1:
            options = list(final_graph[node])

            # sort by level then alphabetically — fully deterministic
            options.sort(key=lambda o: (NV.get(o, 0), o))
            choice    = options[0]   # lowest level (or first alphabetically)
            remaining = options[1]

            final_graph[node].remove(choice)

            pred_of_choice = list(final_graph.get(choice, set()))
            if pred_of_choice and pred_of_choice[0] not in final_graph.get(remaining, set()):
                final_graph[remaining].add(f"{choice}_redundant")
                final_graph[f"{choice}_redundant"] = set(final_graph[choice])
                final_graph.pop(choice, None)
            else:
                final_graph[remaining].add(f"{choice}_dash")

    return final_graph


# ── timing ───────────────────────────────────────────────────────────────────

def earliest_time(X, Ui, topo_order):
    """Earliest finish time for each node."""
    earliest = {}
    for y in topo_order:
        preds = Ui.get(y, set())
        base  = max((earliest[p] for p in preds), default=0)
        earliest[y] = base + X.get(y, 0)
    return earliest


def latest_time(X, U, earliest, topo_order):
    """Latest finish time for each node."""
    latest = {}

    # All nodes with no successors are terminal
    terminals   = [n for n in U if not U.get(n)]
    project_end = max(earliest[n] for n in terminals)
    for n in terminals:
        latest[n] = project_end

    for x in reversed(topo_order):
        if x in latest:
            continue
        succs = [y for y in U.get(x, []) if y in latest]
        if succs:
            # LF[x] = min over successors s of (LF[s] - dur[s])
            latest[x] = min(latest[s] - X.get(s, 0) for s in succs)
        else:
            latest[x] = earliest[x]

    return latest


# ── drawing ──────────────────────────────────────────────────────────────────

def pert_graph(X, Ui, NV, C):
    dot = Digraph("Graphe", format='svg')
    dot.body.append('\tgraph [nodesep=0.8];\n')
    dot.body.append('\tnode [shape=circle];\n')

    Cs = copy.deepcopy(C)

    index = 1
    for x in Ui:
        if "redun" not in x:
            dot.node(x, label=str(index))
            index += 1
        else:
            base = x.replace("_redundant", "")
            lvl  = NV.get(base)
            if lvl is not None and lvl in Cs and base in Cs[lvl]:
                Cs[lvl].remove(base)

    for y in Ui:
        if "redun" in y:
            continue
        for x in Ui[y]:
            if "dash" in x:
                clean = x.replace("_dash", "")
                dot.edge(clean, y, label=f"{clean} (0)", style="dashed")
            elif "redun" in x:
                src          = next(iter(Ui.get(x, [])), None)
                activity     = x.replace("_redundant", "")
                duration     = X.get(activity, 0)
                if src:
                    dot.edge(src, y, label=f"{activity} ({duration})")
            else:
                dot.edge(x, y, label=f"{y} ({X.get(y, 0)})")

    for i in Cs:
        if Cs[i]:
            dot.body.append('{ rank = same; ' + '; '.join(Cs[i]) + '}\n')

    return dot


def final_pert(source, Ui, earliest, latest):
    """Inject EF | LF into every node label."""
    temp = source
    for x in Ui:
        if "redun" in x:
            continue
        marker = f'{x} [label='
        idx = temp.find(marker)
        if idx == -1:
            continue
        idx += len(marker)

        if temp[idx] == '"':
            end     = temp.find('"', idx + 1)
            current = temp[idx + 1:end]
            old = f'{x} [label="{current}"'
        else:
            end     = temp.find(']', idx)
            current = temp[idx:end].strip()
            old = f'{x} [label={current}'

        new  = f'{x} [label="{earliest[x]} | {latest[x]}\\n{current}"'
        temp = temp.replace(old, new, 1)

    return graphviz.Source(temp, filename="Graphe", format="png")


# ── main ─────────────────────────────────────────────────────────────────────

def compute_graph(X, U):
    # First pass: compute levels without DEBUT
    Ui  = UtoUi(U)
    NV  = Niveaux(Ui)
    C   = {}
    for k, v in NV.items():
        C.setdefault(v, []).append(k)

    # Inject DEBUT
    X_full = {"DEBUT": 0, **X}
    U_full = {"DEBUT": set(C[0]), **U}

    Ui_full = UtoUi(U_full)
    NV_full = Niveaux(Ui_full)
    C_full  = {}
    for k, v in NV_full.items():
        C_full.setdefault(v, []).append(k)

    topo    = topological_sort(U_full)
    reduced = transitive_reduction(U_full, Ui_full)
    final   = remove_duplicates(U_full, reduced, NV_full)

    early   = earliest_time(X_full, Ui_full, topo)
    late    = latest_time(X_full, U_full, early, topo)

    graph   = pert_graph(X_full, final, NV_full, C_full)
    pert    = final_pert(graph.source, Ui_full, early, late)
    pert.render()

    # Print float summary for verification
    print(f"{'Task':<8} {'EF':<6} {'LF':<6} {'Float'}")
    print("-" * 28)
    for t in topo:
        ef    = early.get(t, '?')
        lf    = late.get(t, '?')
        f     = (lf - ef) if isinstance(lf, int) and isinstance(ef, int) else '?'
        crit  = " ← critical" if f == 0 else ""
        print(f"{t:<8} {ef:<6} {lf:<6} {f}{crit}")

    return early, late


def display_image(path):
    subprocess.run(["start", path], shell=True)  # Windows
    # Linux: subprocess.run(["xdg-open", path])
    # Mac:   subprocess.run(["open", path])


# ── Example ───────────────────────────────────────────────────────────────

X = {
    "A": 1,
    "B": 1,
    "C": 5,
    "D": 2,
    "E": 2,
    "F": 4,
    "G": 2,
    "H": 2,
    "I": 1,
    "J": 1,
}

U = {
    "A": {"E"},
    "B": {"C", "D"},
    "C": {"G"},
    "D": {"G"},
    "E": {"F"},
    "F": {"H"},
    "G": {"H"},
    "H": {"I"},
    "I": {"J"},
    "J": set(),
}

compute_graph(X, U)
display_image("Graphe.png")

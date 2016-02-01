import networkx as nx
import random
import numpy as np
import operator
import os

def add_unit(g, nodetype={'vertices': 6}):
    if len(g.nodes()) == 0:
        nodenr = 0
        g.add_node(0, nodetype)
    else:
        nodenr = max(g.nodes())+1
        g.add_node(nodenr, nodetype)
    return nodenr

def add_unit_neighbor(g, neighbor, nodetype={'vertices': 6}):
    if g.degree(neighbor) == g.node[neighbor]['vertices']:
        check_closure(g, neighbor)
        return False
    
    if random.random() <= g.defect_level and (g.dense_defect or g.node[neighbor]['vertices'] == 6):
        nodetype = {'vertices': 5}
        if random.random() < 0.5: nodetype = {'vertices': 7}
    
    near_hexagon = True
    nodenr = add_unit(g, nodetype)
    #neighbor = find_neighbor(g)
    g.add_edge(neighbor, nodenr)
    nn = find_neighbor_neighbor(g, nodenr, neighbor)
    if nn:
        g.add_edge(nodenr, nn)
        g.add_edge(neighbor, nn)
        if g.node[nn]['vertices'] != 6: near_hexagon = False
    
    if g.degree(neighbor) == g.node[neighbor]['vertices']:
        nn = find_neighbor_neighbor(g, nodenr, neighbor)
        if nn:
            g.add_edge(nodenr, nn)
            if g.node[nn]['vertices'] != 6: near_hexagon = False

    if not near_hexagon:
        g.node[nodenr]['vertices'] = 6

def find_neighbor(g):
    for n in g.nodes():
        if g.node[n]['vertices'] != g.degree(n):
            return n

def find_neighbor_neighbor(g, node, neighbor):
    neighbors = []
    for n in set(g[neighbor]):
        if n == node or g.node[n]['vertices'] == g.degree(n):
            continue
        shared_neighbors = set(g[n]).intersection(set(g[neighbor]))
        #print(node, neighbor, n, g[n], shared_neighbors)
        if len(shared_neighbors) < 2:
            neighbors.append(n)
    
    if neighbors:
        return neighbors[0]
    else:
        return None

def check_closure(g, node):
    h = g.subgraph(g[node])
    if nx.cycle_basis(h): return True
    sorted_nodes = sorted(h.degree().items(), key=operator.itemgetter(1))
    nodes = [n[0] for n in sorted_nodes[:2] if n[1] == 1]
    if len(nodes) == 2:
        if g.node[nodes[0]]['vertices'] > g.degree(nodes[0]) and \
           g.node[nodes[1]]['vertices'] > g.degree(nodes[1]):
            g.add_edge(nodes[0], nodes[1])
            return False

        if g.node[nodes[0]]['vertices'] > g.degree(nodes[0]) and \
            g.node[nodes[1]]['vertices'] == g.degree(nodes[1]):
            h = g.subgraph(g[nodes[1]])
            sorted_nodes = sorted(h.degree().items(), key=operator.itemgetter(1))
            xnode = [n[0] for n in sorted_nodes if n[1] == 1 and n[0] not in [nodes[0], nodes[1], node]].pop()
            for n in g[xnode]:
                if n in [nodes[1], node]: continue
                g.add_edge(nodes[0], n)
            g.remove_node(xnode)
            return False

        if g.node[nodes[0]]['vertices'] == g.degree(nodes[0]) and \
            g.node[nodes[1]]['vertices'] > g.degree(nodes[1]):
            h = g.subgraph(g[nodes[0]])
            sorted_nodes = sorted(h.degree().items(), key=operator.itemgetter(1))
            xnode = [n[0] for n in sorted_nodes if n[1] == 1 and n[0] not in [nodes[0], nodes[1], node]].pop()
            for n in g[xnode]:
                if n in [nodes[0], node]: continue
                g.add_edge(nodes[1], n)
            g.remove_node(xnode)
            return False

def atom_graph(g):
    # determine if subgroup is attached
    h = nx.Graph()
    v = []
    tris = {}
    edges = {}
    for node,data in g.nodes(data=True):
        g.node[node]['atoms'] = set([])

    # triplet
    for node in nx.nodes(g):
        for each in g[node]:
            if each == node: continue
            neighbors = set(g[node]).intersection(set(g[each]))
            #print(node, each, neighbors, set(g[node]), g[each], set(g[each]))
            for neighbor in neighbors:
                t = tuple(sorted((node, each, neighbor)))
                if t not in list(tris.keys()):
                    nr = len(h.nodes())
                    tris[t] = nr
                    h.add_node(nr)
                    g.node[node]['atoms'].add(nr)
                    g.node[each]['atoms'].add(nr)
                    g.node[neighbor]['atoms'].add(nr)
                    #print(node, each, neighbor)
                    for k in tris:
                        if len(set(k).intersection(set(t))) == 2:
                            h.add_edge(nr, tris[k])
                            edges[tuple(sorted(set(k).intersection(set(t))))] = nr

    #if nx.cycle_basis(h):
    #    extra_nodes = set(h.nodes()).difference(set(np.concatenate(nx.cycle_basis(h))))
    #    for n in extra_nodes:
    #        h.remove_node(n)
    return h

def build_initial_pdb(g, pos, fname='junk.pdb'):
    v = []
    count = 1
    atom_xyz = {}
    atom_names = {}
    line = "ATOM %6i %4s%4s%6i    %8.3f%8.3f%8.3f%6.2f%6.2f      %-4s\n"
    atomtype = 'C'
    residue = 'GP'
    resnr = 1
    x = 0
    y = 0
    z = 0
    bfactor = 0
    segment = 'GP'

    rot = lambda theta: np.matrix(((np.cos(np.radians(theta)), -np.sin(np.radians(theta)), 0), 
                                    (np.sin(np.radians(theta)), np.cos(np.radians(theta)), 0),
                                    (0, 0, 0)))
    fp = open(fname, 'w')
    for i,node in enumerate(g.nodes()):
        atoms = g.node[node]['atoms']
        if not atoms: continue
        source = sorted(atoms)[0]
        u = np.array((1.39, 0, 0))
        theta = 0
        center = (0.0,0.0)
        
        for atom in sorted(atoms):
            if atom in atom_xyz: continue
            if atom not in pos: continue
            v = np.asarray(np.dot(u,rot(theta)))[0,:]
            x = v[0] + center[0]
            y = v[1] + center[1]
            x = pos[atom][0]/10
            y = pos[atom][1]/10

            atomtype = "C%x" % count
            atom_names[atom] = atomtype
            atomdata = (count,atomtype,residue,resnr,x,y,z,0.0,bfactor,segment[:4])
            atom_xyz[atom] = np.array((x,y,z))
            #print(line % atomdata)
            fp.write(line % atomdata)
            count += 1
            theta += 60
    fp.close()
    return atom_names

def build_topology(h, atom_names, fname='graphene.rtf'):
    v = []
    atom_names = {}
    count = 1
    fp = open(fname, 'w')
    fp.write("""*  --------------------------------------------------------------------------  *
*          GRAPHENE                                                            *
*  --------------------------------------------------------------------------  *
*
36  1

MASS    23 HGR61    1.00800  ! aromatic H
MASS    61 CG2R61  12.01100  ! 6-mem aromatic C

DEFA FIRS NONE LAST NONE
AUTO ANGLES DIHE

RESI GP 0.0
""")
    for atom in h.nodes():
        if h.degree(atom) < 1: continue
        atom_names[atom] = "C%x" % count
        count += 1
        if count % 2 == 0:
            fp.write("GROUP\n")
        fp.write("ATOM %s CG2R61 0.0\n" % atom_names[atom])
        
    for atom_edge in h.edges():
        fp.write("BOND %s %s\n" % (atom_names[atom_edge[0]], atom_names[atom_edge[1]]))
    fp.close()

if __name__ == '__main__':
    g = nx.Graph()
    add_unit(g)
    closed_node = []
    for i in range(700):
        node = find_neighbor(g)
        nodetype = g.node[node]['vertices']
        for j in range(nodetype):
            add_unit_neighbor(g, node)
        
        for n in g.nodes():
            if n not in closed_node and g.node[n]['vertices'] == g.degree(n):
                check_closure(g, n)
                closed_node.append(n)

    h = atom_graph(g)
    pos=nx.graphviz_layout(h, prog='neato')
    atom_names = build_initial_pdb(h, pos)
    build_topology(h, atom_names)

    os.system('~/local/charmm/c40a2 < test.inp > test.out')

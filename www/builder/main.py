from flask import Flask, render_template, request, redirect, url_for, session, abort, send_file
from werkzeug import secure_filename
from flask import jsonify
import os
import filecmp
import uuid
import sqlite3
from flask import g
from datetime import datetime
import conf
import subprocess as sp

ALLOWED_EXTENSIONS = set(['pdb'])

app = Flask(__name__)
app.config['JOB_FOLDER'] = conf.JOB_FOLDER

def get_job_folder(uuid):
    return os.path.join(conf.JOB_FOLDER, uuid)

# main

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tutorial')
def tutorial():
    return render_template('404.html')

@app.route('/about')
def about():
    return render_template('404.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('404.html')
    mail_sent = False
    if request.method == 'POST':
        email = request.form['email']
        text = request.form['text'].strip()
        if email and text:
            from flask_mail import Mail, Message
            mail = Mail(app)
            msg = Message('[ANMPathway] comment from a user', sender=email, recipients=[conf.ADMIN_EMAIL, conf.EXTRA_EMAIL])
            msg.body = text
            mail.send(msg)
            mail_sent = True
    
    return render_template('contact.html', mail_sent=mail_sent)

@app.route('/download/<uuid>/<filename>')
@app.route('/download/<uuid>', defaults={'filename': None})
def download(uuid, filename):
    jobdir = get_job_folder(uuid)
    if not os.path.exists(jobdir): abort(404)

    filename = os.path.join(jobdir, 'graphene.pdb')
    if not os.path.exists(filename): abort(404)
    fp = open(filename)
    return send_file(fp, as_attachment=True, attachment_filename=os.path.basename(filename))

@app.route('/success/<uuid>')
def success(uuid):
    return render_template('success.html', uuid=uuid)

@app.route('/build', methods=['get', 'post'])
def build():
    from build import *
    import networkx as nx

    jobid = str(uuid.uuid4())
    os.mkdir(get_job_folder(jobid))

    nrings = int(request.form['nrings'])
    defect = float(request.form['defect']) / 100

    g = nx.Graph()
    g.defect_level = defect
    add_unit(g)
    closed_node = []
    for i in range(nrings):
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
    pdbname = '%s/junk.pdb' % get_job_folder(jobid)
    rtfname = '%s/graphene.rtf' % get_job_folder(jobid)
    atom_names = build_initial_pdb(g, pos, pdbname)
    build_topology(h, atom_names, rtfname)

    from shutil import copy
    copy('static/charmm/graphene.prm', get_job_folder(jobid))
    copy('static/charmm/mini.inp', get_job_folder(jobid))

    import subprocess as sp
    p = sp.Popen([conf.CHARMM_BINARY, '-i', 'mini.inp'], cwd=get_job_folder(jobid))
    p.wait()

    return redirect(url_for('success', uuid=jobid))

if __name__ == '__main__':
    app.debug = True
    app.run()

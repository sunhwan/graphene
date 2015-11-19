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
app.config['UPLOAD_FOLDER'] = conf.UPLOAD_FOLDER
app.config['JOB_FOLDER'] = conf.JOB_FOLDER


# main

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
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

    if filename:
        filename = os.path.join(jobdir, os.path.basename(filename))
        if not os.path.exists(filename): abort(404)
        fp = open(filename)
        if filename.endswith('gif'):
            return send_file(fp, as_attachment=False, attachment_filename=os.path.basename(filename))
        return send_file(fp, as_attachment=True, attachment_filename=os.path.basename(filename))

    else:
        import tarfile
        import StringIO, glob
        fp = StringIO.StringIO()
        tar = tarfile.open(fileobj=fp, mode='w:gz')
        excludes = ['taskmanager.py', 'err', 'out', 'run.pbs']
        for f in glob.glob('%s/*' % jobdir):
            if os.path.basename(f) in excludes: continue
            tar.add(f, arcname='anmpathway/%s' % os.path.basename(f))
        tar.close()
        fp.seek(0)
        return send_file(fp, mimetype='application/x-gzip', as_attachment=True, attachment_filename='anmpathway.tar.gz')

@app.route('/success/<uuid>')
def success(uuid):
    return render_template('success.html', uuid=uuid)

@app.route('/', methods=['GET', 'POST'])
def pathfinder():
    return redirect(url_for('success', uuid=jobid))

if __name__ == '__main__':
    app.debug = True
    app.run()

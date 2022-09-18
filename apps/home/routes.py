# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import sys
from apps.home import blueprint
from flask import render_template, request, flash, url_for, session
from flask_login import login_required
from jinja2 import TemplateNotFound
from apps.authentication.models import Users, Employees, Departments, Jobs
from apps import db, login_manager, s3_bucket


@blueprint.route('/index')
@login_required
def index():    
    print(f'session key: {session.get("key")}', file=sys.stdout)    
    return render_template('home/index.html', segment='index')


@blueprint.route('/<template>')
@login_required
def route_template(template):

    try:

        if not template.endswith('.html'):
            template += '.html'

        # Detect the current page
        segment = get_segment(request)

        # Serve the file (if exists) from app/templates/home/FILE.html
        return render_template("home/" + template, segment=segment)

    except TemplateNotFound:
        return render_template('home/page-404.html'), 404

    except:
        return render_template('home/page-500.html'), 500

@blueprint.route('/employees_add',methods=('GET','POST'))
@login_required
def employees_add():    
    departments = Departments.query.all()
    jobs = Jobs.query.all()
    if request.method == 'POST':
        form = request.form.to_dict()
        username = form["username"]
        # password = form["password"]
        email = form["email"]        
        profile_pic = request.files        
        
        print(f'username: {form["username"]}', file=sys.stdout)
        print(f'password: {form["password"]}', file=sys.stdout)        
        print(f'pic: {profile_pic}', file=sys.stdout)        

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            flash('Username has been taken', 'error')
            return render_template('home/employees_add.html', segment='employees', form=form, departments=departments, jobs=jobs)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            flash('The email is already taken', 'error')
            return render_template('home/employees_add.html', segment='employees', form=form, departments=departments, jobs=jobs)

        is_admin=True if form["is_admin"] else False
        form.pop("is_admin",None)
        # else we can create the user
        user = Users(**form,is_admin=is_admin)
        db.session.add(user)
        db.session.flush()        
        employee = Employees(**form,user_id=user.id)
        db.session.add(employee)
        db.session.flush()
        try:            
            emp_img_name = "emp-id-" + str(employee.id) + "_image_file"
            s3_bucket.put_object(Key=emp_img_name, Body=profile_pic)
        except:           
            db.session.rollback()
            flash('The email is already taken', 'error')
            return render_template('home/employees_add.html', segment='employees', form=form, departments=departments, jobs=jobs)            
        db.session.commit()        
        
        return render_template('home/employees.html', segment='employees')
    
    print(f'departments: {departments}', file=sys.stdout)
    print(f'jobs: {jobs}', file=sys.stdout)
    return render_template('home/employees_add.html', segment='employees_add', departments=departments, jobs=jobs)


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None

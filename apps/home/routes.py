# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import sys
from decouple import config
from apps.home import blueprint
from flask import render_template, request, flash, url_for, session, redirect, url_for
from flask_login import login_required
from jinja2 import TemplateNotFound
from apps.authentication.models import Users, Employees, Departments, Jobs, token_required
from apps import db, login_manager, s3_bucket, s3_bucket_location


@blueprint.route('/index')
@token_required
def index():    
    # print(f'home session key: {session.get("key")}', file=sys.stdout)    
    # print(f'home session user_auth: {session.get("user_auth")}', file=sys.stdout)
    print(f'index auth_token: {session.get("auth_token")}', file=sys.stdout)
    return render_template('home/index.html', segment='index')


@blueprint.route('/<template>')
@token_required
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

@blueprint.route('/employees')
@token_required
def employees():

    employees = Employees.query.all()

    object_url = "https://s3-{0}.amazonaws.com/{1}/".format(
        s3_bucket_location,
        config("STORAGE_BUCKET")            
    )

    print(f"object_url: {object_url}", file=sys.stdout)
    return render_template('home/employees.html', segment='employees', object_url=object_url, employees=employees)

@blueprint.route('/employees_add',methods=('GET','POST'))
@token_required
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
            return render_template('home/employees_add.html', segment='employees_add', form=form, departments=departments, jobs=jobs)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            flash('The email is already taken', 'error')
            return render_template('home/employees_add.html', segment='employees_add', form=form, departments=departments, jobs=jobs)

        is_admin=True if form["is_admin"] else False
        form.pop("is_admin",None)
        # else we can create the user
        user = Users(**form,is_admin=is_admin)
        db.session.add(user)
        db.session.flush()        
        employee = Employees(**form,user_id=user.id)
        db.session.add(employee)
        db.session.flush()
        
        emp_img_name = "emp-id-" + str(employee.id) + "-profile-pic"
        try:            
            s3_bucket.put_object(Key=emp_img_name, Body=profile_pic)
        except:           
            db.session.rollback()
            flash('There is something wrong when inserting the data', 'error')
            return render_template('home/employees_add.html', segment='employees_add', form=form, departments=departments, jobs=jobs)            
        db.session.commit()        
        
        return redirect(url_for('home_blueprint.employees'))
    
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

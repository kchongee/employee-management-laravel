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
from apps import db, login_manager, s3_bucket, s3_bucket_location, s3_client, object_url
from apps.home.util import output_flash_msg


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

    print(f"object_url: {object_url}", file=sys.stdout)
    print(f"employees: {employees}", file=sys.stdout)
    output_flash_msg()
    return render_template('home/employees.html', segment='employees', object_url=object_url, employees=employees)

@blueprint.route('/employees/create',methods=('GET','POST'))
@token_required
def employees_create():    
    departments = Departments.query.all()
    jobs = Jobs.query.all()
    if request.method == 'POST':
        form = request.form.to_dict()
        username = form["username"]
        # password = form["password"]
        email = form["email"]        
        profile_pic = request.files["profile_pic"]       
        
        print(f'username: {form["username"]}', file=sys.stdout)
        print(f'password: {form["password"]}', file=sys.stdout)        
        print(f'pic: {profile_pic}', file=sys.stdout)        

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            session["flash_msg"] = {'msg':'Username has been taken','type':'warning'}
            return employees_create()         

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            session["flash_msg"] = {'msg':'The email is already taken','type':'warning'}
            return employees_create()

        # convert the binary value to boolean
        is_admin=True if form["is_admin"] else False
        form.pop("is_admin",None)
        # else we can create the user
        user = Users(**form,is_admin=is_admin)
        db.session.add(user)
        db.session.flush()        
        employee = Employees(**form,user_id=user.id)
        db.session.add(employee)
        db.session.flush()
        
        emp_img_name = config("EMP_IMG_PREF") + str(employee.id)
        try:          
            print(s3_bucket)  
            s3_bucket.put_object(Key=emp_img_name, Body=profile_pic)
        except:           
            db.session.rollback()
            print("something wrong when put object into s3")  
            session["flash_msg"] = {'msg':'There is something wrong when inserting the data','type':'warning'}
            return employees_create()
        db.session.commit()        
        session["flash_msg"] = {'msg':'The user is created','type':'success'}
        return redirect(url_for('home_blueprint.employees'))
    
    print(f'departments: {departments}', file=sys.stdout)
    print(f'jobs: {jobs}', file=sys.stdout)
    output_flash_msg()
    return render_template('home/employees_create.html', segment='employees_create', departments=departments, jobs=jobs)


@blueprint.route('/employees/detail/<id>',methods=('GET','POST'))
@token_required
def employees_detail(id):    
    print(f'view employee detail with employee id: {id}', file=sys.stdout)
    user = Users.query.filter_by(id=id).first()
    employee = Employees.query.filter_by(id=id).first()

    if not (user and employee):
        session["flash_msg"] = {'msg':f'Failed to retrieve employee with id: {id}','type':'warning'}
        return redirect(url_for('home_blueprint.employees'))

    output_flash_msg()
    return render_template('home/employees_detail.html', segment='employees_detail', employee=employee, user=user, object_url=object_url)


@blueprint.route('/employees/update/<id>',methods=['GET','POST'])
@token_required
def employees_update(id):
    print(f'update?: {id}', file=sys.stdout)
    user = Users.query.filter_by(id=id).first()
    employee = Employees.query.filter_by(id=id).first()
    employees = Employees.query.all()
    if request.method == 'POST':
        form = request.form.to_dict()
        username = form["username"]
        # password = form["password"]
        email = form["email"]        
        profile_pic = request.files["profile_pic"]                       

         # Check username exists
        user = Users.query.filter_by(username=username).first()
        if user:
            session["flash_msg"] = {'msg':'Username has been taken','type':'warning'}
            return employees_update(id)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            session["flash_msg"] = {'msg':'The email is already taken','type':'warning'}
            return employees_update(id)

        is_admin=True if form["is_admin"] else False
        form.pop("is_admin",None)

        db.session.query(Users).filter(id=id).update(form)
        db.session.commit()
        db.session.query(Employees).filter(id=id).update(form)
        db.session.commit()                
        
        emp_img_name = config("EMP_IMG_PREF") + str(employee.id)
        try:          
            print(s3_bucket)  
            s3_bucket.put_object(Key=emp_img_name, Body=profile_pic)
        except:           
            db.session.rollback()
            print("something wrong when put object into s3")  
            flash('There is something wrong when inserting the data', 'error')
            return redirect(url_for('home_blueprint.employees'))
        db.session.commit()        
        
        return redirect(url_for('home_blueprint.employees'))
    else:
        user = Users.query.filter_by(id=id).first()
        employee = Employees.query.filter_by(id=id).first()

        if not (user and employee):
            session["flash_msg"] = {'msg':f'There is something wrong when retrieving employee with id: {id}','type':'danger'}
            return employees_update(id)
        
    return render_template('home/employees_update.html', segment='employees_update', employees=employees, employee=employee, user=user)

@blueprint.route('/employees/delete/<id>')
@token_required
def employees_delete(id):            
    user_to_delete = Users.query.filter_by(id=id).first()
    employee_to_delete = Employees.query.filter_by(id=id).first()
    db.session.delete(user_to_delete)    
    db.session.delete(employee_to_delete)
    try:          
        s3_client.delete_object(Bucket=config("STORAGE_BUCKET"),Key=config("EMP_IMG_PREF")+str(id))
    except:           
        db.session.rollback()
        print("something wrong when delete object from s3")          
        session["flash_msg"] = {'msg':f'There is something wrong when delete the emp with id:{id}','type':'danger'}
        return redirect(url_for('home_blueprint.employees'))
    db.session.commit()            

    session["flash_msg"] = {'msg':f'Successfully deleted the employee','type':'success'}
    return redirect(url_for('home_blueprint.employees'))    


# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None

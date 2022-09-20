# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import sys
import jwt
from flask import render_template, redirect, request, url_for, session
from flask_login import (
    current_user,
    login_user,
    logout_user
)
from decouple import config
from datetime import timedelta
from apps import db, login_manager, elasticache_redis
from apps.authentication import blueprint
from apps.authentication.forms import LoginForm, CreateAccountForm
from apps.authentication.models import Users, Employees, Departments, Jobs, token_required
from apps.authentication.util import verify_pass

ACCESS_EXPIRES = timedelta(hours=1)

@blueprint.route('/')
def route_default():    
    for department in ["Marketing","Operations","Finance","Sales","HR"]:        
        try:            
            department_record = Departments(title=department)        
            db.session.add(department_record)
            db.session.commit()     
        except:
            print(f'cant save the departments', file=sys.stdout)
            break

    for job in ["Full Stack Developer","Data Scientist","Cloud Engineer","DevOps Engineer","Software Engineer"]:
        try:            
            job_record = Jobs(title=job)        
            db.session.add(job_record)
            db.session.commit()                 
        except:
            print(f'cant save the jobs', file=sys.stdout)        
            break
     
    return redirect(url_for('authentication_blueprint.login'))


# Login & Registration

@blueprint.route('/login', methods=['GET', 'POST'])
def login():            
    login_form = LoginForm(request.form)
    if 'login' in request.form:

        # read form data
        username = request.form['username']
        password = request.form['password']

        # Locate user
        user = Users.query.filter_by(username=username).first()        
        # Check the password
        if user and verify_pass(password, user.password):

            # login_user(user)
            auth_token = jwt.encode({'id': user.id}, config('SECRET_KEY'), 'HS256')
            session['auth_token'] = auth_token
            # double_auth_token = jwt.encode({'auth_token': auth_token}, config('SECRET_KEY'), 'HS256')
            # session['double_auth_token'] = double_auth_token
            print(f'login auth_token: {session.get("auth_token")}', file=sys.stdout)
            # print(f'login double_auth_token: {session.get("double_auth_token")}', file=sys.stdout)
            elasticache_redis.set(auth_token,1,ACCESS_EXPIRES)
            # elasticache_redis.set(double_auth_token,auth_token,ACCESS_EXPIRES)
            return redirect(url_for('authentication_blueprint.route_default'))

        # Something (user or pass) is not ok
        return render_template('accounts/login.html',
                               msg='Wrong user or password',
                               form=login_form)

    # if not current_user.is_authenticated:
    if not session.get("auth_token"):
        return render_template('accounts/login.html',
                               form=login_form)
    return redirect(url_for('home_blueprint.index'))


@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    create_account_form = CreateAccountForm(request.form)
    if 'register' in request.form:

        username = request.form['username']
        email = request.form['email']

        # Check usename exists
        user = Users.query.filter_by(username=username).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Username already registered',
                                   success=False,
                                   form=create_account_form)

        # Check email exists
        user = Users.query.filter_by(email=email).first()
        if user:
            return render_template('accounts/register.html',
                                   msg='Email already registered',
                                   success=False,
                                   form=create_account_form)

        # else we can create the user
        user = Users(**request.form,is_admin=1)        
        db.session.add(user)
        # employee = Employees(**request.form,age=22)
        # db.session.add(employee)
        db.session.commit()        
        

        return render_template('accounts/register.html',
                               msg='User created please <a href="/login">login</a>',
                               success=True,
                               form=create_account_form)

    else:
        return render_template('accounts/register.html', form=create_account_form)


@blueprint.route('/logout')
def logout():
    # logout_user()
    elasticache_redis.delete(session.get("auth_token"))
    session.pop("auth_token")
    return redirect(url_for('authentication_blueprint.login'))


# Errors

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(403)
def access_forbidden(error):
    return render_template('home/page-403.html'), 403


@blueprint.errorhandler(404)
def not_found_error(error):
    return render_template('home/page-404.html'), 404


@blueprint.errorhandler(500)
def internal_error(error):
    return render_template('home/page-500.html'), 500

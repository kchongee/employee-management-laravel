import sys
from decouple import config
from apps.home import blueprint
from flask import render_template, request, flash, url_for, session, redirect, url_for
from flask_login import (
    login_required,
    current_user,
    login_user,
    logout_user
)
from jinja2 import TemplateNotFound
from apps.authentication.models import Users, Departments, Jobs, token_required
from apps import db, login_manager, s3_bucket, s3_bucket_location, s3_client, object_url, elasticache_redis
from apps.home.util import output_flash_msg
from apps.authentication.util import verify_pass, hash_pass


@blueprint.route('/index')
@login_required
def index():        
    if(elasticache_redis.get(f"user-{current_user.id}")):
        return redirect(url_for('home_blueprint.employees'))
    return render_template('home/page-403.html'), 403
    # return render_template('home/index.html', segment='index')


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

@blueprint.route('/employees')
@login_required
def employees():

    employees = Users.query.filter(Users.id!=current_user.id).all()

    print(f"object_url: {object_url}", file=sys.stdout)
    print(f"employees: {employees}", file=sys.stdout)
    output_flash_msg()
    return render_template('home/employees.html', segment='employees', object_url=object_url, employees=employees)

@blueprint.route('/employees/create',methods=('GET','POST'))
@login_required
def employees_create():
    departments = Departments.query.all()
    jobs = Jobs.query.all()
    if request.method == 'POST':
        form = request.form.to_dict()
        username = form["username"]
        # password = form["password"]
        email = form["email"]        
        profile_pic = request.files["profile_pic"]
        department = form["department"]
        job = form["job"]
        
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

        check_deparment = Departments.query.filter_by(title=department).first()
        if not check_deparment:
            new_department = Departments(title=department)
            db.session.add(new_department)
            db.session.flush()  

        check_job = Jobs.query.filter_by(title=department).first()
        if not check_job:
            new_job = Jobs(title=job)
            db.session.add(new_job)
            db.session.flush()  

        print(f'form: {form}', file=sys.stdout)
        # convert the binary value to boolean
        is_admin=True if int(form["is_admin"]) else False
        form.pop("is_admin",None)
        # else we can create the user
        user = Users(**form,is_admin=is_admin)
        db.session.add(user)
        db.session.flush()        
        # employee = Employees(**form,user_id=user.id)
        # db.session.add(employee)
        # db.session.flush()
        
        emp_img_name = config("EMP_IMG_PREF") + str(user.id)
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
@login_required
def employees_detail(id):    
    print(f'view employee detail with employee id: {id}', file=sys.stdout)
    employee = Users.query.filter_by(id=id).first()
    # employee = Employees.query.filter_by(id=id).first()

    # if not (user and employee):
    if not employee:
        session["flash_msg"] = {'msg':f'Failed to retrieve employee with id: {id}','type':'warning'}
        return redirect(url_for('home_blueprint.employees'))

    output_flash_msg()
    return render_template('home/employees_detail.html', segment='employees_detail', employee=employee, object_url=object_url)


@blueprint.route('/employees/update/<id>',methods=['GET','POST'])
@login_required
def employees_update(id, employee=None):
    print(f'update?: {id}', file=sys.stdout)

    # if not (user and employee):
    # employees = Employees.query.all()
    if not employee:
        employee = Users.query.filter_by(id=id).first()

    if request.method == 'POST':
        form = request.form.to_dict()
        username = form["username"]
        email = form["email"]
        profile_pic = request.files["profile_pic"]
        department = form["department"]
        job = form["job"]

        check_employee = Users.query.filter(Users.username==username,Users.id!=id).first()
        # Check username exists                
        if check_employee:
            print(f'check employee found(username): {check_employee}', file=sys.stdout)
            session["flash_msg"] = {'msg':'Username has been taken','type':'warning'}
            return employees_update(id,employee=employee)

        check_employee = Users.query.filter(Users.email==email,Users.id!=id).first()
        # Check email exists        
        if check_employee:
            print(f'check employee found(email): {check_employee}', file=sys.stdout)
            session["flash_msg"] = {'msg':'The email is already taken','type':'warning'}
            return employees_update(id,employee=employee)

        check_deparment = Departments.query.filter_by(title=department).first()
        if not check_deparment:
            new_department = Departments(title=department)
            db.session.add(new_department)
            db.session.flush()  

        check_job = Jobs.query.filter_by(title=department).first()
        if not check_job:
            new_job = Jobs(title=job)
            db.session.add(new_job)
            db.session.flush()

        form["is_admin"] = True if int(form["is_admin"]) else False        
        db.session.query(Users).filter(Users.id==id).update(form)
        db.session.commit()
        # db.session.query(Employees).filter(id=id).update(form)
        # db.session.commit()
        
        emp_img_name = config("EMP_IMG_PREF") + str(employee.id)
        if profile_pic:        
            try:
                print(s3_bucket)  
                s3_bucket.put_object(Key=emp_img_name, Body=profile_pic)
            except:           
                db.session.rollback()
                print("something wrong when put object into s3")  
                session["flash_msg"] = {'msg':'There is something wrong when putting the object into s3','type':'warning'}
                return employees_update(id,employee=employee)
            db.session.commit()        
        
        session["flash_msg"] = {'msg':'Update successfull','type':'success'}
        return redirect(url_for('home_blueprint.employees_detail',id=id))
    else:        
        # if not (user and employee):
        if not employee:
            session["flash_msg"] = {'msg':f'There is something wrong when retrieving employee with id: {id}','type':'danger'}
            return redirect(url_for('home_blueprint.employees'))
    
    departments = Departments.query.all()
    jobs = Jobs.query.all()
    output_flash_msg()
    return render_template('home/employees_update.html', segment='employees_update', employee=employee, object_url=object_url, departments=departments, jobs=jobs)

@blueprint.route('/employees/delete/<id>')
@login_required
def employees_delete(id):            
    user_to_delete = Users.query.filter_by(id=id).first()
    db.session.delete(user_to_delete)    
    # employee_to_delete = Employees.query.filter_by(id=id).first()
    # db.session.delete(employee_to_delete)
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

@blueprint.route('/employees/change_password/<id>',methods=['GET','POST'])  
@login_required
def employees_change_password(id):
    if request.method == 'POST':       
        print(f'come in post? ', file=sys.stdout) 
        form = request.form.to_dict()
        old_password = form["old_password"]
        new_password = form["new_password"]
        confirm_password = form["confirm_password"]
        
        check_employee = Users.query.filter_by(id=id).first()
        if not verify_pass(old_password, check_employee.password):
            print(f'verify password: {check_employee}', file=sys.stdout)
            session["flash_msg"] = {'msg':'You have entered the wrong old password','type':'danger'}
            return redirect(url_for('home_blueprint.employees_change_password',id=id))

        if new_password != confirm_password:                
            print(f'check employee found(username): {check_employee}', file=sys.stdout)
            session["flash_msg"] = {'msg':"New password doesn't match",'type':'danger'}
            return redirect(url_for('home_blueprint.employees_change_password',id=id))
        
        check_employee.password = hash_pass(new_password)
        db.session.commit()   # check this line
        # db.session.filter_by(id=id).update()            
        
        session["flash_msg"] = {'msg':'Password changed successfully','type':'success'}
        return redirect(url_for('home_blueprint.employees_detail',id=id))

    output_flash_msg()
    return render_template('home/employees_change_password.html', segment='employees_change_password', id=id)    

# Helper - Extract current page name from request
def get_segment(request):

    try:

        segment = request.path.split('/')[-1]

        if segment == '':
            segment = 'index'

        return segment

    except:
        return None

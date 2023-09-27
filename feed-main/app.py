from flask import Flask,redirect,url_for,render_template,request,flash,abort,session
from flask_session import Session
import matplotlib.pyplot as plt
from key import secret_key,salt1,salt2,salt3
from stoken import token
import flask_excel as excel
from cmail import sendmail
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
import random
import string
import os
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
excel.init_excel(app)
#mydb=mysql.connector.connect(host='localhost',user='root',password='sgnk@143',db='feed')
db = os.environ['RDS_DB_NAME']
user = os.environ['RDS_USERNAME']
password = os.environ['RDS_PASSWORD']
host = os.environ['RDS_HOSTNAME']
port = os.environ['RDS_PORT']
with mysql.connector.connect(host=host, user=user, password=password, db=db) as conn:
    cursor = conn.cursor(buffered=True)
    cursor.execute('CREATE TABLE IF NOT EXISTS users(username varchar(15) primary  key,email varchar(80) unique,password varchar(15),email_status enum("confirmed","not confirmed") default "not confirmed")')
    cursor.execute('CREATE TABLE IF NOT EXISTS survey(uname varchar(15),sid varchar(20), time int, url text, date timestamp default now() on update now(),foreign key(uname) references users(username))')
    cursor.execute('CREATE TABLE IF NOT EXISTS formdata(sid varchar(20),fname varchar(30),username varchar(30), email varchar(30) primary key, q1 int, q2 varchar(5), q3 int, q4 varchar(5), q5 int, q6 varchar(5), q7 int, q8 int, q9 varchar(15), q10 varchar(100))')
mydb = mysql.connector.connect(host=host, user=user, password=password, db=db)

@app.route('/')
def index():
    return render_template('title.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))

    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',[username,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/time',methods=['GET','POST'])
def time():
    
        if request.method=="POST":
            username=session.get("user")
            time=int(request.form['timestamp'])
            cursor=mydb.cursor(buffered=True)
            cursor.execute("select email from users where username=%s",[username])
            email=cursor.fetchone()[0]
            sid = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(5)])
            url=url_for('feed',sid=sid,time=time,fname=username,token=token(email,salt=salt3),_external=True)
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into survey(uname,sid,url,time) values(%s,%s,%s,%s)',[username,sid,url,time])
            mydb.commit()
            print(type(time))
            return render_template("homepage.html")
        else:
            return render_template("timestamp.html")
  

@app.route('/feed/<token>/<time>/<fname>/<sid>',methods=['GET','POST'])
def feed(token,time,fname,sid):
    #cursor=mydb.cursor(buffered=True)
    #cursor.execute("select time from survey where sid=%s",[sid])
    #max_age=cursor.fetchone()[0]
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt3,max_age=int(time))
    except Exception as e:
        print(e)
        abort(404,'Link Expired')
    else:
        if request.method=="POST":
            username=request.form['name']
            email=request.form['email']
            q1=request.form['question1']
            q2=request.form['question2']
            q3=request.form['question3']
            q4=request.form['question4']
            q5=request.form['question5']
            q6=request.form['question6']
            q7=request.form['question7']
            q8=request.form['question8']
            q9=request.form['question9']
            q10=request.form['question10']
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from formdata where email=%s',[email])
            count=cursor.fetchone()[0]
            if count==1:
                flash("feedback alredy given with this email")
                return render_template('feedback.html')
            else:
                
                cursor=mydb.cursor(buffered=True)
                cursor.execute('insert into formdata values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',[sid,fname,username,email,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10])
                mydb.commit()
                return render_template("feedbackmsg.html")
        else:
            return render_template('feedback.html')

@app.route('/sfeed')
def sfeed():
    return render_template("sfeed.html")

@app.route('/view')
def view():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select sid,url,date from survey where uname=%s',[username])
      
        data1=cursor.fetchall()
        return render_template('table.html',data1=data1)
    else:
        return render_template("login.html")
    
@app.route('/getnotesdata/<nid>')
def getdata(nid):
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        columns=['username','email','q1','q2','q3','q4','q5','q6','q7','q8','q9','q10']
        cursor.execute('select username,email,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10 from formdata where fname=%s and sid=%s',[username,nid])
        data=cursor.fetchall()
        array_data=[list(i) for i in data]
        array_data.insert(0,columns)
        return excel.make_response_from_array(array_data,'xlsx',filename='feedbackdata')
    else:
        return redirect(url_for('login'))

@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('feed'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))

@app.route('/homepage',methods=['GET','POST'])
def home():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return render_template('homepage.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))

@app.route('/resendconfirmation')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))

@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('registration.html')
    return render_template('registration.html')
    
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))

@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')

@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2)
    except:
    
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))

if __name__=='__main__':
    app.run()
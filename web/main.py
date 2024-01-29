from flask import Flask, request, send_from_directory, render_template, jsonify, session, url_for, redirect, flash
import os
import datetime
# db
import pymysql
import pymysql.cursors
# pw 암호화
from passlib.hash import pbkdf2_sha256 
import cv2
import numpy as np

# 비디오 처리
from io import BytesIO
import base64
from PIL import Image

# 음성인식
import speech_recognition as sr
# from moviepy.editor import VideoFileClip
import subprocess

# S3
import boto3

from m_config import AWS_ACCESS_KEY, AWS_SECRET_ACCESS_KEY
from m_config import AWS_S3_BUCKET_NAME, AWS_S3_BUCKET_REGION



db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')

app = Flask(__name__)


# 함수 선언

def s3_connection():
    '''
    s3 bucket에 연결
    :return: 연결된 s3 객체
    '''
    try:
        s3 = boto3.client(
            service_name='s3',
            region_name=AWS_S3_BUCKET_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )
    except Exception as e:
        print(e)
        exit(ERROR_S3_CONNECTION_FAILED)
    else:
        print("s3 bucket connected!")
        return s3

def s3_put_object(s3, bucket, filepath, access_key):
    '''
    s3 bucket에 지정 파일 업로드
    :param s3: 연결된 s3 객체(boto3 client)
    :param bucket: 버킷명
    :param filepath: 파일 위치
    :param access_key: 저장 파일명
    :return: 성공 시 True, 실패 시 False 반환
    '''
    try:
        s3.upload_file(filepath, bucket, access_key)
    except Exception as e:
        print(e)
        return False
    return 'SUCCESS'
    
def s3_get_object(s3, bucket, object_name, file_name):
    '''
    s3 bucket에서 지정 파일 다운로드
    :param s3: 연결된 s3 객체(boto3 client)
    :param bucket: 버킷명
    :param object_name: s3에 저장된 object 명
    :param file_name: 저장할 파일 명(path)
    :return: 성공 시 True, 실패 시 False 반환
    '''
    try:
        s3.download_file(bucket, object_name, file_name)
    except Exception as e:
        print(e)
        return False
    return True


s3 = s3_connection()



 
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'




def hash_password(original_password):
    salt = 'yh*hello123'
    password = original_password + salt
    password = pbkdf2_sha256.hash(password)
    return password
 
def check_password(original_password, hashed_password):
    # 이미 라이브러리가 있다.
    salt = 'yh*hello123'
    check = pbkdf2_sha256.verify(original_password+salt, hashed_password)
    # True인지 False인지 체크를 해준다.
    return check






def recognize_speech(video_file_path, filename):
    # 동영상을 WAV 파일로 변환
    # video = mp.VideoFileClip(video_file_path)
    print('command')
    command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(video_file_path, filename + '.wav')
    print('filename')
    subprocess.call(command, shell=True)
    print('call')
    # with VideoFileClip(video_file_path) as video:
    #     video.audio.write_audiofile(filename + '.wav')
    # 음성 인식 객체 생성
    recognizer = sr.Recognizer()


    # 동영상 파일에서 음성을 추출하고 음성을 텍스트로 변환
    with sr.AudioFile( filename + '.wav') as source:
        audio = recognizer.record(source)  # 음성 추출
        if not audio: 
            print('오디오가 없음')

    try:
        text = recognizer.recognize_google(audio, language = "ko")  # Google 웹 서비스를 사용하여 음성을 텍스트로 변환
        return text
    except sr.UnknownValueError:
        print("음성을 인식할 수 없습니다.")
        text = '음성을 인식할 수 없습니다.'
        return text 
    except sr.RequestError as e:
        print(f"Google 웹 서비스에 접근할 수 없습니다. 에러: {e}")
    return None




# 라우트 시작 

@app.route("/")
def home():
    if session.get('logged_in'):
        return render_template('index_ori.html')
    else:
        return render_template('index.html')
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')
        name = request.form['username']
        password = request.form['password']


        # SQL 쿼리 실행
        cursor = db.cursor()
        select_query = "SELECT user_id FROM user"
        cursor.execute(select_query)
        user_id_list = cursor.fetchall()
        
        id_list = [user_id[0] for user_id in user_id_list]

        cursor = db.cursor()
        query = "SELECT password FROM user WHERE user_id = %s"
        cursor.execute(query, (name,))
        hash_pw = cursor.fetchone()

        cursor = db.cursor()
        query = "SELECT name FROM user WHERE user_id = %s"
        cursor.execute(query, (name,))
        user_name = cursor.fetchone()

        cursor = db.cursor()
        query = "SELECT visit1, visit2, visit3 FROM user WHERE user_id = %s"
        cursor.execute(query, (name,))
        visit = cursor.fetchone()

        
        if name == '' or password == '' or hash_pw == None :
            flash('입력이 잘못되었습니다.')
            return render_template('login.html') 
        
        check = check_password(password, hash_pw[0])
        try:
            if (name in id_list):
                if (check):
                    #2번을 해보세요!
                    session["logged_in"] = True
                        #3번을 해보세요!
                    session['user'] = {'id' : name, 'username' : user_name[0], 'visit1' : visit[0], 'visit2' : visit[1], 'visit3' : visit[2] } 
                    # session['user_id'] = user_name[0] // user_id 는 숫자 값이 들어가야 함
                    # return render_template('index_ori.html', id = name)
                    session['ans1'] = 0
                    session['ans2'] = 0
                    session['ans3'] = 0
                    return redirect('home')
                        #4번을 해보세요!
                else:
                    return '비밀번호가 틀립니다.'
            return '아이디가 없습니다.'
        except:
            return 'Dont login'
    else:
        return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')
        #4번을 해보세요!
        id = request.form['id']

        password = request.form['password']
        mail = request.form['mail']

        name = request.form['name']
        course = request.form['course']

        hash_pw = hash_password(password)

        if id == '' or password == '' or mail == '' or name == '' : 
            flash('입력이 잘못되었습니다.')
            return render_template('register.html')

        # SQL 쿼리 실행
        cursor = db.cursor()
        select_query = "SELECT user_id FROM user"
        cursor.execute(select_query)
        user_id_list = cursor.fetchall()
        
        id_list = [user_id[0] for user_id in user_id_list]
        if id in id_list: 
            return '아이디가 중복됩니다.'

        # SQL 쿼리 실행
        cursor = db.cursor()
        select_query = "SELECT mail FROM user"
        cursor.execute(select_query)
        user_mail_list = cursor.fetchall()
        
        mail_list = [user_mail[0] for user_mail in user_mail_list]
        if mail in mail_list: 
            return '메일이 중복됩니다.'

        
        # SQL 쿼리 실행
        cursor = db.cursor()
        insert_query = "INSERT INTO user (user_id, password, mail, name, course) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(insert_query, (id, hash_pw, mail, name, course))
        
        # 변경 내용을 커밋
        db.commit()
        # 커서 닫기
        cursor.close()

        return redirect(url_for('login'))
    else:
        return render_template('register.html')
    

@app.route("/logout")
def logout():
    session['logged_in'] = False
    session['user'] = {'id' : "", 'username' : ""}
    # return render_template('index.html')
    return redirect('login')


# 아이디 찾기 라우트
@app.route('/forgot_id', methods=['GET', 'POST'])
def forgot_id():
    if request.method == 'POST':
        mail = request.form['mail']
        name = request.form['name']

        if mail == '' or name == '' : 
            flash('입력이 잘못되었습니다.')
            return render_template('forgot_id.html')

        cursor = db.cursor()
        select_query = "SELECT mail, name FROM user"
        cursor.execute(select_query)
        user_info_list = cursor.fetchall()

        for info in user_info_list : 
            if info[0] == mail and info[1] == name :
                session['is_authenticated'] = True
                session['mail'] = mail
                # return render_template('new_password.html')
                return redirect(url_for('idfind'))
    else: 
        return render_template('forgot_id.html')



@app.route('/idfind', methods=['GET'])
def idfind(): 
    if session['is_authenticated'] == True : 
        session['is_authenticated'] = False
        
        mail = session['mail']
        session['mail'] = ''

        cursor = db.cursor()
        select_query = "SELECT user_id, mail FROM user"
        cursor.execute(select_query)
        user_info_list = cursor.fetchall()

        for info in user_info_list: 
            if info[1] == mail:
                id = info[0]

        return render_template('find_id.html', id = id )
    else : 
        return redirect(url_for('home'))


# 비밀번호 찾기 라우트
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        id = request.form['id']
        mail = request.form['mail']
        name = request.form['name']

        if id == '' or mail == '' or name == '': 
            flash('입력이 잘못되었습니다.')
            return render_template('forgot_password.html')

        cursor = db.cursor()
        select_query = "SELECT user_id, mail, name FROM user"
        cursor.execute(select_query)
        user_info_list = cursor.fetchall()

        for info in user_info_list : 
            if info[0] == id and info[1] == mail and info[2] == name :
                session['is_authenticated'] = True
                # return render_template('new_password.html')
                return redirect(url_for('new_password', id = id ))
    else: 
        return render_template('forgot_password.html')


@app.route('/new_password/<id>', methods=['GET', 'POST'])
def new_password(id): 
    if session['is_authenticated'] == True : 
        session['is_authenticated'] = False
        if request.method == 'POST':
                password = request.form['password']
                hash_pw = hash_password(password) 
                
                cursor = db.cursor()
                update_query = "UPDATE user SET password = %s WHERE user_id = %s "
                cursor.execute(update_query, (hash_pw, id ))
            
                # 변경 내용을 커밋
                db.commit()
                # 커서 닫기
                cursor.close()
                return redirect(url_for('login'))
        else : 
            return render_template('new_password.html')
    else : 
        return redirect(url_for('home'))

#   ////////////// 로그인 구현


@app.route("/home")
def homepage():
    if session.get('logged_in'):
        user_data = session.get('user', {})
        
        if user_data:
            id = user_data.get('id')
            name = user_data.get('username')
        # id = session['user']
        return render_template('index_ori.html', id = name )
    else :
        return render_template('index.html')




@app.route('/sr', methods = ['POST'])
def speech(): 
    video = request.files['video']
    if session.get('logged_in'):
        user_data = session.get('user', {})
        
        if user_data:
            id = user_data.get('id')
            name = user_data.get('username')
        # 파일을 저장하거나 처리합니다.
        filename = "test.webm"
        directory = 'uploads/'
        # video.save(id + '_' + name  + '_' + filename)
        video.save(directory + id + '_' + name  + '_' + filename)
        video_file_path = directory + id + '_' + name  + '_' + filename

        output_file = f"{video_file_path.replace('.webm', '.mp4')}"

        # ffmpeg 명령어 실행
        command = f"ffmpeg -i {video_file_path} -r 30 {output_file}"
        # !{command}
        subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, text=True)
        os.remove(video_file_path)
        print('remove webm')

        # audio_name = directory + id + '_' + name  + '_' + 'audio'
        audio_name = directory + id + '_' + name  + '_' + 'audio'
        print(audio_name)
        speech_text = recognize_speech(output_file, audio_name)
        
        print('audio remove')
        os.remove(audio_name + '.wav')
        print('output remove')
        os.remove(output_file)
        # return redirect(url_for('test'))
        # return render_template('answer.html', text = text)
        return speech_text
    else :
        return render_template('index.html')
    # return redirect(url_for('test'))



@app.route('/upload', methods=['POST'])
def upload_video():
    video = request.files['video']
    ans = session['ans']
    if video:
        user_data = session.get('user', {})
        
        if user_data:
            id = user_data.get('id')
            name = user_data.get('username')
        # 파일을 저장하거나 처리합니다.
        filename = f"{ans}.webm"
        print(filename)
        directory = 'uploads/'
        video.save(directory + id + '_' + name  + '_' + filename)
        ret = s3_put_object(s3, AWS_S3_BUCKET_NAME, directory  + id + '_' + name  + '_' + filename, id + '_' + name  + '_' + filename)
        if ret :
            print("파일 저장 성공")
        else:
            print("파일 저장 실패")
        os.remove(directory + id + '_' + name  + '_' + filename)

        return '파일 업로드 성공', 200
    return '파일을 찾을 수 없습니다', 400




# 가상의 유저 정보 (예시로 사용)
users = {'123456': 'user_password'}


@app.route('/login2', methods=['POST'])
def login2():
    if request.method == 'POST':
        data = request.get_json()  # JSON 데이터 수신

        serial_number = data.get('serialNumber')  # 전송된 일련번호 가져오기

        # 일련번호를 가상의 유저 정보와 비교하여 로그인 처리
        if serial_number in users:
            response = {'message': '로그인 성공'}
            return jsonify(response), 200
        else:
            response = {'message': '로그인 실패: 유저 정보가 일치하지 않습니다'}
            return jsonify(response), 401




@app.route('/camera_test')
def test(): 
    if session.get('logged_in'):
        session['ans'] = 'test'
        return render_template('camera_test.html')
    else :
        return render_template('index.html')
    




@app.route('/prof_pic')
def prof(): 
    if session.get('logged_in'):
        return render_template('profile_pic.html')
    else :
        return render_template('index.html')



@app.route('/capture', methods=['POST'])
def capture():
    if request.method == 'POST':
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')
        user_data = session.get('user', {})
        id = user_data.get('id')

        def save_image_to_mysql(image_data):
            try:
                with db.cursor() as cursor:
                    # 이미지 데이터를 MySQL에 저장
                    update_query = "UPDATE user SET image = %s WHERE user_id = %s"
                    cursor.execute(update_query, (image_data, id))
                    db.commit()
            except pymysql.Error as e:
                print(f"MySQL 오류: {e}")

        data = request.get_json()

        if 'image_data' in data:
            # 이미지 데이터를 저장하거나 처리하는 로직을 추가할 수 있습니다.
            # 여기서는 간단하게 콘솔에 출력합니다.
            print('프로필 사진 촬영')

            image_data_decoded = base64.b64decode(data['image_data'].split(',')[1])

            # 이미지 데이터를 MySQL에 저장
            save_image_to_mysql(image_data_decoded)

        image_data = data['image_data'].split(',')[1]  # Remove 'data:image/jpeg;base64,' part
        image_bytes = base64.b64decode(image_data)

        # Process the image (you can add your own image processing logic here)
        # For example, resizing the image to a fixed size
        image = Image.open(BytesIO(image_bytes))
        image = image.resize((200, 200))

        # Save the processed image
        processed_image_path = 'processed_image.jpg'
        image.save(processed_image_path)
        
        return jsonify({'processed_image_path': processed_image_path})
        


@app.route('/interview')
def inter(): 
    if session.get('logged_in'):
        session['ans'] = 'ans1'
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')
        user_data = session.get('user', {}) 
        id = user_data.get('id')
        print(user_data) 
        if user_data:
            visit1 = user_data.get('visit1')
            print(visit1)
            if visit1 != 1 :
                if session['ans1'] != 1 :
                    session['ans1'] = 1
                    visit1 = 1
                    print(type(visit1))
                    cursor = db.cursor()
                    update_query = "UPDATE user SET visit1 = %s WHERE user_id = %s "
                    cursor.execute(update_query, (visit1, id ))
                    
                    # 변경 내용을 커밋
                    db.commit()
                    # 커서 닫기
                    cursor.close()
                    return render_template('webcam.html')
                else:
                    flash('이미 응시하셨습니다')
                    return render_template('webcam_done1.html')
            else:
                flash('이미 응시하셨습니다')
                return render_template('webcam_done1.html')
    else :
        return render_template('index.html')




@app.route('/interview2')
def inter2(): 
    if session.get('logged_in'):
        session['ans'] = 'ans2'
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')

        user_data = session.get('user', {})
        id = user_data.get('id')
        print(user_data)
        if user_data:
            visit2 = user_data.get('visit2')
            print(visit2)
            if visit2 != 1 :
                if session['ans2'] != 1:
                    session['ans2'] = 1
                    visit2 = 1
                    print(type(visit2))
                    cursor = db.cursor()
                    update_query = "UPDATE user SET visit2 = %s WHERE user_id = %s "
                    cursor.execute(update_query, (visit2, id ))
                    
                    # 변경 내용을 커밋
                    db.commit()
                    # 커서 닫기
                    cursor.close()
                    return render_template('webcam2.html')
                else:
                    flash('이미 응시하셨습니다')
                    return render_template('webcam_done2.html')
            else:
                flash('이미 응시하셨습니다')
                return render_template('webcam_done2.html')
    else :
        return render_template('index.html')




@app.route('/interview3')
def inter3(): 
    if session.get('logged_in'):
        session['ans'] = 'ans3'
        db = pymysql.connect(host='127.0.0.1', user='intview_user', password='0000', db='intview', charset='utf8')
        user_data = session.get('user', {})
        id = user_data.get('id')
        print(user_data)
        if user_data:
            visit3 = user_data.get('visit3')
            print(visit3)
            if visit3 != 1 : 
                if session['ans3'] != 1 :
                    session['ans3'] = 1
                    visit3 = 1
                    print(type(visit3))
                    cursor = db.cursor()
                    update_query = "UPDATE user SET visit3 = %s WHERE user_id = %s "
                    cursor.execute(update_query, (visit3, id ))
                    
                    # 변경 내용을 커밋
                    db.commit()
                    # 커서 닫기
                    cursor.close()
                    return render_template('webcam3.html')
                else:
                    flash('이미 응시하셨습니다')
                    return render_template('webcam_done3.html')
            else:
                flash('이미 응시하셨습니다')
                return render_template('webcam_done3.html')
    else :
        return render_template('index.html')


@app.route('/result')
def result(): 
    if session.get('logged_in'):
        return render_template('result.html')
    else :
        return render_template('index.html')


if __name__ == '__main__':

    app.logger.info("test") 
    app.logger.debug("debug test") 
    app.logger.error("error test") 
    # app.run(debug=True)
    app.run(host="0.0.0.0", port ="80",debug=True)


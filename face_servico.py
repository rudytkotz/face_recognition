from os import listdir, remove
from os.path import isfile, join, splitext

import face_recognition
import base64
import psycopg2
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Armazenamento global para imagens
faces_dict = {}
persistent_faces = "/root/faces"

# Create flask app
app = Flask(__name__)
CORS(app)

# <Picture functions> #
def conecta_db():
  con = psycopg2.connect(host='localhost', 
                         database='API_Hospital',
                         user='postgres', 
                         password='root')
  return con


def consultar_db(sql):
  con = conecta_db()
  cur = con.cursor()
  cur.execute(sql)
  recset = cur.fetchall()
  registros = []
  for rec in recset:
    registros.append(rec)
  con.close()
  return registros

def convert_base64(file_stream):
    with open(file_stream, "rb") as image2string: 
        converted_string = base64.b64encode(image2string.read()) 
    print(converted_string) 
    with open('encode.bin', "wb") as file: 
        file.write(converted_string)
    return converted_string

def base64_ToImage(encode):
    return base64.b64decode((encode)) 
     
def is_picture(filename):
    image_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in image_extensions


def get_all_picture_files(path):
    files_in_dir = [join(path, f) for f in listdir(path) if isfile(join(path, f))]
    return [f for f in files_in_dir if is_picture(f)]


def remove_file_ext(filename):
    return splitext(filename.rsplit('/', 1)[-1])[0]

def calc_face_encoding(image):
    # Currently only use first face found on picture
    loaded_image = face_recognition.load_image_file(image)
    faces = face_recognition.face_encodings(loaded_image)

    # If more than one face on the given image was found -> error
    if len(faces) > 1:
        raise Exception(
            "Encontrou mais de um rosto na imagem.")

    # If none face on the given image was found -> error
    if not faces:
        raise Exception("Não foram identificadas faces na imagem.")

    return faces[0]


def get_faces_dict(path):
    image_files = get_all_picture_files(path)
    return dict([(remove_file_ext(image), calc_face_encoding(image))
        for image in image_files])

def encoding_img(image):
    img = face_recognition.load_image_file(image)

    # Get face encodings for any faces in the uploaded image
    uploaded_faces = face_recognition.face_encodings(img)
    return str(uploaded_faces)

def detect_faces_in_image(file_stream):
    # Load the uploaded image file
    img = face_recognition.load_image_file(file_stream)

    # Get face encodings for any faces in the uploaded image
    uploaded_faces = face_recognition.face_encodings(img)
    

    # Defaults for the result object
    faces_found = len(uploaded_faces)
    faces = []

    if faces_found:
        face_encodings = list(faces_dict.values())
        for uploaded_face in uploaded_faces:
            match_results = face_recognition.compare_faces(
                face_encodings, uploaded_face)
            for idx, match in enumerate(match_results):
                if match:
                    match = list(faces_dict.keys())[idx]
                    match_encoding = face_encodings[idx]
                    dist = face_recognition.face_distance([match_encoding],
                            uploaded_face)[0]
                    faces.append({
                        "id": match,
                        "dist": dist,
                        "encoding": str(uploaded_faces)
                    })

    return {
        "count": faces_found,
        "faces": faces
    }

# <Picture functions> #

# <Controller>

@app.route('/base', methods=['POST'])
def web_recognize_base():
    if 'base64Image' not in request.args:
        raise BadRequest("Identifier for the face was not given!")

    base64ToImagem = request.args.get('base64Image')
    
    file = extract_image(base64_ToImage(base64ToImagem))

    if file and is_picture(file.filename):
        # The image file seems valid! Detect faces and return the result.
        return jsonify(detect_faces_in_image(file))
    else:
        raise BadRequest("Given file is invalid!")


@app.route('/faces', methods=['GET', 'POST', 'DELETE'])
def web_faces_base_public():
    # GET
    if request.method == 'GET':
        return jsonify(list(faces_dict.keys()))

    # POST/DELETE
    if 'base64Image' not in request.args:
        raise BadRequest("Identifier for the face was not given!")

    base64ToImagem = request.args.get('base64Image')
    
    file = extract_image(base64_ToImage(base64ToImagem))
    if 'id' not in request.args:
        raise BadRequest("Identifier for the face was not given!")

    if request.method == 'POST':
        app.logger.info('%s loaded', file.filename)
        # HINT jpg included just for the image check -> this is faster then passing boolean var through few methods
        # TODO add method for extension persistence - do not forget abut the deletion
        file.save("{0}/{1}.jpg".format(persistent_faces, request.args.get('id')))
        try:
            new_encoding = calc_face_encoding(file)
            faces_dict.update({request.args.get('id'): new_encoding})

        except Exception as exception:
            raise BadRequest(exception)

    elif request.method == 'DELETE':
        faces_dict.pop(request.args.get('id'))
        remove("{0}/{1}.jpg".format(persistent_faces, request.args.get('id')))

    return jsonify(list(faces_dict.keys()))


@app.route('/', methods=['POST'])
def web_recognize():
    file = extract_image(request)

    if file and is_picture(file.filename):
        # The image file seems valid! Detect faces and return the result.
        return jsonify(detect_faces_in_image(file))
    else:
        raise BadRequest("Given file is invalid!")


@app.route('/faces', methods=['GET', 'POST', 'DELETE'])
def web_faces():
    # GET
    if request.method == 'GET':
        return jsonify(list(faces_dict.keys()))

    # POST/DELETE
    file = extract_image(request)
    if 'id' not in request.args:
        raise BadRequest("Identifier for the face was not given!")

    if request.method == 'POST':
        app.logger.info('%s loaded', file.filename)
        # HINT jpg included just for the image check -> this is faster then passing boolean var through few methods
        # TODO add method for extension persistence - do not forget abut the deletion
        file.save("{0}/{1}.jpg".format(persistent_faces, request.args.get('id')))
        try:
            new_encoding = calc_face_encoding(file)
            faces_dict.update({request.args.get('id'): new_encoding})

        except Exception as exception:
            raise BadRequest(exception)

    elif request.method == 'DELETE':
        faces_dict.pop(request.args.get('id'))
        remove("{0}/{1}.jpg".format(persistent_faces, request.args.get('id')))

    return jsonify(list(faces_dict.keys()))

@app.route('/face', methods=['POST'])
def web_faces_atual():
    
    # POST

    #img = Image.open(io.BytesIO(base64.decodebytes(bytes(base64_str, "utf-8"))))

    file = extract_image(img)
    
    if request.method == 'POST':
        try:
            new_encoding = calc_face_encoding(file)
            enco = encoding_img(file)

        except Exception as exception:
            raise BadRequest(exception)

    return enco, img


def extract_image(request):
    # Check if a valid image file was uploaded
    if 'file' not in request.files:
        raise BadRequest("Missing file parameter!")

    file = request.files['file']
    if file.filename == '':
        raise BadRequest("Given file is invalid")

    return file
# </Controller>


if __name__ == "__main__":
    print("Starting by generating encodings for found images...")
    # Calculate known faces
    faces_dict = get_faces_dict(persistent_faces)
    print(faces_dict)

    # Start app
    print("Starting WebServer...")
    app.run(host='0.0.0.0', port=8080, debug=False)

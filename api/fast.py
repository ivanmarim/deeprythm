from fastapi import FastAPI, File, UploadFile, Form
from data.pdf_proc import convert_to_images, output_ecgs, remove_grid
from data.params import smsng_crop_areas, smote_class_dict, full_name_rythm, apple_crop_areas
from fastapi.middleware.cors import CORSMiddleware
import shutil
from models.final_model import model_load_compile
import tensorflow as tf
import base64


app = FastAPI()


# Allowing all middleware is optional, but good practice for dev purposes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

#to use it use <your_url>/predict?some_input=<hola>
@app.get("/predict")
def predict(some_input: str):
    return {'prediction': 'some prediction'}

@app.post("/upload")
async def upload_file(device: str = Form(...), file: UploadFile = File(...)):
    #device = files.get('device', 'Samsung')
    with open(f"{file.filename}", "wb") as pdf_file:
        shutil.copyfileobj(file.file, pdf_file)

    # Crop the Samsung ECG, convert to images and remove gridlines
    if device == 'Apple':
        output_ecgs(file.filename, apple_crop_areas)
    else:
        output_ecgs(file.filename, smsng_crop_areas)
    convert_to_images('ecg2.pdf', 'ecg2.jpg')
    remove_grid('ecg2.jpg', 'ecg2_no_grid.jpg')

    # Load the model
    model = model_load_compile('models/base_model_fulldata_2.h5')

    #Take one ecg picture to make a prediction
    img = tf.keras.preprocessing.image.load_img('ecg2_no_grid.jpg')

    # Resize the image to match the target shape
    new_height, new_width = 79, 622  # Specify the target height and width
    resized_img = tf.image.resize(img, (new_height, new_width))

    # Expand the dimensions to create a batch with a single image
    input_img = tf.expand_dims(resized_img, axis=0)

    # Make predictions
    predictions_list = model.predict(input_img).tolist()[0]
    prediction = predictions_list.index(max(predictions_list))
    category = smote_class_dict[prediction]
    full_name = full_name_rythm[category]

    # Read images as binary data
    with open('ecg2.jpg', 'rb') as f:
        image1_data = f.read()
    with open('ecg2_no_grid.jpg', 'rb') as f:
        image2_data = f.read()

    # Encode images as base64 strings
    image1_base64 = base64.b64encode(image1_data).decode('utf-8')
    image2_base64 = base64.b64encode(image2_data).decode('utf-8')

    return {'image': image1_base64,
            'image_nogrid': image2_base64,
            'prediction': full_name}


@app.post("/uploadecg")
async def upload_ecg(file: UploadFile = File(...)):
    with open(f"{file.filename}", "wb") as jpg_file:
        shutil.copyfileobj(file.file, jpg_file)

    #Take one ecg picture to make a prediction
    img = tf.keras.preprocessing.image.load_img(file.filename)

    # Resize the image to match the target shape
    new_height, new_width = 79, 622  # Specify the target height and width
    resized_img = tf.image.resize(img, (new_height, new_width))

    # Expand the dimensions to create a batch with a single image
    input_img = tf.expand_dims(resized_img, axis=0)

    # Load the model
    model = model_load_compile('models/base_model_fulldata_2.h5')
    # Make predictions
    predictions_list = model.predict(input_img).tolist()[0]
    prediction = predictions_list.index(max(predictions_list))
    category = smote_class_dict[prediction]
    full_name = full_name_rythm[category]

    # Read images as binary data
    with open(file.filename, 'rb') as f:
        image_data = f.read()

    # Encode images as base64 strings
    image_base64 = base64.b64encode(image_data).decode('utf-8')
    return {'image': image_base64,
            'prediction': full_name}

@app.get("/")
def root():
    return {'greeting': 'Hello'}

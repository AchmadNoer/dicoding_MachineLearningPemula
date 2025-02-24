# -*- coding: utf-8 -*-
"""Proyek Akhir Model Deployment Dicoding.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/179pj39JXZM816qwByT0yyq9cfEbGJNAs

Dataset Source: https://www.kaggle.com/datasets/andrewmvd/animal-faces

## Setting Up Data
"""

! pip install -q kaggle

from google.colab import files

files.upload() # select kaggle.json file

! mkdir ~/.kaggle

! cp kaggle.json ~/.kaggle

! chmod 600 ~/.kaggle/kaggle.json

! kaggle datasets download andrewmvd/animal-faces

! unzip animal-faces.zip

! pip install seedir

import seedir as sd

sd.seedir('/content/afhq', itemlimit=3, style='emoji')

"""## Merge Data"""

main_dir = "/content/afhq"

import os
import subprocess

! rm -rf "/content/merged"

for folder in sorted(os.listdir(main_dir+"/train")):
    train_path = main_dir + "/train/" + folder 
    val_path = main_dir + "/val/" + folder
    dataset_path = '/content/merged'
    rsync_cmd = 'rsync' + ' -avzh ' + train_path + ' ' + val_path + ' ' + dataset_path
    subprocess.run(rsync_cmd, shell=True)

sd.seedir('/content/merged', itemlimit=3, style='emoji')

"""## Split Data"""

! pip install split-folders

import splitfolders

! rm -rf '/content/Datasets'

splitfolders.ratio('/content/merged', output="Datasets", ratio=(0.8, 0.2))

train_dir = "/content/Datasets/train"
validation_dir = "/content/Datasets/val"

"""## Augmentation"""

from keras.preprocessing.image import ImageDataGenerator

train_datagen = ImageDataGenerator(
    rotation_range=5,
    width_shift_range=0.05,
    height_shift_range=0.05,
    zoom_range=0.05,
    fill_mode='nearest',
    rescale=1./255
)

validation_datagen = ImageDataGenerator(rescale=1./255)

train_generator = train_datagen.flow_from_directory(
        train_dir,
        target_size=(64, 64),
        batch_size=32,
        class_mode='categorical')

validation_generator = validation_datagen.flow_from_directory(
        validation_dir,
        target_size=(64, 64),
        batch_size=8,
        class_mode='categorical')

"""## Create Model"""

import tensorflow as tf

model = tf.keras.models.Sequential([
    tf.keras.layers.Conv2D(32, (3,3), padding = 'same', activation='relu', input_shape=(64, 64, 3)),
    tf.keras.layers.Conv2D(64, (3,3), padding = 'same', activation='relu'),
    tf.keras.layers.MaxPooling2D(3, 3),
    tf.keras.layers.Dropout(0.2),

    tf.keras.layers.Conv2D(64, (3,3), padding = 'same', activation='relu'),
    tf.keras.layers.Conv2D(128, (3,3), padding = 'same', activation='relu'),
    tf.keras.layers.MaxPooling2D(3, 3),
    tf.keras.layers.Dropout(0.2),

    tf.keras.layers.Conv2D(128, (3,3), padding = 'same', activation='relu'),
    tf.keras.layers.Conv2D(256, (3,3), padding = 'same', activation='relu'),
    tf.keras.layers.MaxPooling2D(3, 3),
    tf.keras.layers.Dropout(0.2),

    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu'),
    tf.keras.layers.BatchNormalization(),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(3, activation='softmax')
])

model.summary()

model.compile(loss='categorical_crossentropy', optimizer=tf.optimizers.Adam(learning_rate=0.0005), metrics=['accuracy'])

from keras.callbacks import EarlyStopping, ReduceLROnPlateau

es = EarlyStopping(
    monitor='val_loss',
    min_delta=0.0001,
    patience=10,
    verbose=1,
    mode='auto'
)

lr = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.2,
    patience=3,
    verbose=1,
    mode='auto',
    min_delta=0.0001,
    min_lr=0.000001
)

import datetime

logdir = os.path.join("history_logs", datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
tb = tf.keras.callbacks.TensorBoard(logdir, histogram_freq=1)

history = model.fit(
      train_generator,
      validation_data=validation_generator,
      epochs=100,
      steps_per_epoch=32,
      validation_steps=8,
      callbacks=[es,lr,tb],
      verbose=1)

"""## Training Result"""

import matplotlib.pyplot as plt

plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='lower right')
plt.show()

plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper right')
plt.show()

plt.plot(history.history['lr'])
plt.title('learning rate')
plt.ylabel('lr')
plt.xlabel('epoch')
plt.show()

# Commented out IPython magic to ensure Python compatibility.
# %load_ext tensorboard
# %tensorboard --logdir history_logs

"""## Save Model"""

import pathlib

export_dir = 'saved_model/'
tf.saved_model.save(model, export_dir)
 
converter = tf.lite.TFLiteConverter.from_saved_model(export_dir)
tflite_model = converter.convert()
 
tflite_model_file = pathlib.Path('animal_faces.tflite')
tflite_model_file.write_bytes(tflite_model)
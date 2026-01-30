import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split

# ==========================================
# CONFIGURATION
# ==========================================
BATCH_SIZE = 64
EPOCHS = 25
LEARNING_RATE = 0.001
DATA_PATH = "processed_data"
MODEL_SAVE_PATH = "models"

print(f"TensorFlow Version: {tf.__version__}")
print(f"Num GPUs Available: {len(tf.config.list_physical_devices('GPU'))}")

# ==========================================
# 1. TINYML MODEL (ARDUINO SAFE)
# ==========================================
def build_tinyml_fall_model(input_shape):
    inputs = keras.Input(shape=input_shape)

    # Block 1
    x = layers.Conv1D(32, 5, activation='relu', padding='same')(inputs)
    x = layers.MaxPooling1D(2)(x)

    # Block 2
    x = layers.Conv1D(64, 5, activation='relu', padding='same')(x)
    x = layers.MaxPooling1D(2)(x)

    # Block 3
    x = layers.Conv1D(64, 3, activation='relu', padding='same')(x)

    # Reduce time dimension
    x = layers.GlobalAveragePooling1D()(x)

    # Dense head
    x = layers.Dense(32, activation='relu')(x)
    x = layers.Dropout(0.2)(x)

    # 2 outputs → fall / no fall
    outputs = layers.Dense(2, activation='softmax')(x)

    return keras.Model(inputs, outputs, name="TinyML_Fall_Detector")

# ==========================================
# 2. DATA LOADING
# ==========================================
def load_data():
    print("Loading data...")
    X = np.load(f"{DATA_PATH}/X_data.npy").astype("float32")
    y = np.load(f"{DATA_PATH}/y_data.npy").astype("int32")  # labels must be 0 or 1

    print(f"Data Shape: {X.shape}")
    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# ==========================================
# 3. TRAINING & EXPORT
# ==========================================
def main():
    if not os.path.exists(MODEL_SAVE_PATH):
        os.makedirs(MODEL_SAVE_PATH)

    X_train, X_test, y_train, y_test = load_data()

    model = build_tinyml_fall_model(input_shape=(200, 12))
    model.summary()

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    print("\nTraining...")
    model.fit(
        X_train, y_train,
        batch_size=BATCH_SIZE,
        epochs=EPOCHS,
        validation_data=(X_test, y_test),
        callbacks=[
            keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True),
            keras.callbacks.ModelCheckpoint(f"{MODEL_SAVE_PATH}/best_model.keras", save_best_only=True)
        ]
    )

    loss, acc = model.evaluate(X_test, y_test)
    print(f"\nFinal Test Accuracy: {acc*100:.2f}%")

    # ==========================================
    # 4. EXPORT TO TFLITE (INT8 QUANTIZED)
    # ==========================================
    print("\nConverting to TensorFlow Lite...")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    # Representative dataset for full integer quantization
    def representative_data_gen():
        for i in range(100):
            yield [X_train[i:i+1]]

    converter.representative_dataset = representative_data_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_model = converter.convert()

    tflite_path = f"{MODEL_SAVE_PATH}/fall_model_int8.tflite"
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)

    print(f"✅ TFLite model saved to: {tflite_path}")
    print("Upload THIS file to Edge Impulse (BYOM)")

if __name__ == "__main__":
    main()

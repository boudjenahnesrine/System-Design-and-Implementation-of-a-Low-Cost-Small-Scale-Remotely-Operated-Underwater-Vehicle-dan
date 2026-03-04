import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5 import QtWidgets
import sys
import cv2
import psutil
import pygame
import serial
import numpy as np
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QProgressBar, QFrame
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer

pygame.init()
pygame.joystick.init()

# Initialiser la manette
if pygame.joystick.get_count() == 0:
    print("Aucune manette détectée")
    sys.exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

# Connexion série
ser = serial.Serial(port='COM11', baudrate=115200, timeout=1)


def lire_commandes():
    pygame.event.pump()
    y_gauche = -joystick.get_axis(1)
    rt = joystick.get_axis(5)
    lt = joystick.get_axis(4)
    rt = (rt + 1) / 2
    lt = (lt + 1) / 2
    bouton_a = joystick.get_button(0)  # 0 pour A
    bouton_b = joystick.get_button(1)  # 1 pour B
    return y_gauche, rt, lt,bouton_a,bouton_b



def envoyer_donnees(k, n, s, d, r):
    data = f"{k:.2f},{n:.2f},{s:.2f},{d:.2f},{r:.2f}\n"
    print(data)
    ser.write(data.encode('utf-8'))


class BubbleDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.temperature = 0.0
        self.pitch = 0.0
        self.roll = 0.0
        self.zoom_factor = 1.0
        self.etat_laser = 0
        self.etat_precedent_bouton_a = 0
        self.etat_led = 0
        self.etat_precedent_bouton_b = 0
        self.setWindowTitle("Bubble - Drone Sous-Marin")
        self.setGeometry(100, 100, 1000, 650)
        self.setStyleSheet("""
            QWidget {
                background-color: #121926;
                color: white;
                font-family: 'Segoe UI', sans-serif;
                font-size: 16px;
            }
            QPushButton {
                background-color: #34495e;
                color: white;
                padding: 12px;
                border-radius: 15px;
                font-size: 16px;
                transition: background-color 0.3s ease;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f75b7;
            }
        """)

        main_layout = QVBoxLayout(self)

        # ===== LAYOUT PRINCIPAL (CAMERA + CONTROLES LED/LASER) =====
        top_layout = QHBoxLayout()
        # ===== BARRE DE COMMANDE EN HAUT =====
        top_bar = QHBoxLayout()
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.clicked.connect(self.zoom_in)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.clicked.connect(self.zoom_out)

        self.recording = False
        self.record_button = QPushButton("⏺️  Démarrer l'enregistrement")
        self.record_button.clicked.connect(self.toggle_recording)
        button_style = """
                           QPushButton {
                               background-color: #5dade2; 
                               color: white;
                               padding: 10px 20px;
                               border: none;
                               border-radius: 10px;
                               font-size: 20px;
                               font-weight: bold;
                           }
                           QPushButton:hover {
                               background-color: #1565c0;
                           }
                           QPushButton:pressed {
                               background-color: #0d47a1;
                           }
                       """

        zoom_in_btn.setStyleSheet(button_style)
        zoom_out_btn.setStyleSheet(button_style)
        self.record_button.setStyleSheet(button_style)

        top_bar.addWidget(zoom_in_btn)
        top_bar.addWidget(zoom_out_btn)
        top_bar.addWidget(self.record_button)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)
        # ===== CAMERA =====
        self.camera_view = QLabel()
        self.camera_view.setFixedSize(800, 400)
        self.camera_view.setStyleSheet("background-color: black; border-radius: 15px; border: 2px solid #2980b9;")
        top_layout.addWidget(self.camera_view)

        # ===== CONTROLES LED / LASER =====
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(20)

        self.led_status = QLabel("💡 LED : OFF")
        self.laser_status = QLabel("🔦 Laser : OFF")
        self.led_status.setAlignment(Qt.AlignLeft)
        self.laser_status.setAlignment(Qt.AlignLeft)

        for label in [self.led_status, self.laser_status]:
            label.setAlignment(Qt.AlignLeft)
            label.setStyleSheet("""
                padding: 10px;
                font-size: 18px;
                background-color: #34495e;
                color: white;
                border-radius: 12px;
                margin-bottom: 15px;
                font-weight: bold;
            """)

        toggle_led = QPushButton("Activer/Désactiver LED")
        toggle_led.setStyleSheet("""
                    QPushButton {
                        background-color: #1e88e5;
                        color: white;
                        font-size: 16px;
                        padding: 12px;
                        border-radius: 10px;
                        margin-bottom: 15px;
                    }
                    QPushButton:hover {
                        background-color: #1abc9c;
                    }
                    QPushButton:pressed {
                        background-color: #1e88e5;
                    }
                """)
        toggle_led.clicked.connect(self.toggle_led)

        toggle_laser = QPushButton("Activer/Désactiver Laser")
        toggle_laser.setStyleSheet("""
                    QPushButton {
                        background-color: #1e88e5;
                        color: white;
                        font-size: 16px;
                        padding: 12px;
                        border-radius: 10px;
                        margin-bottom: 15px;
                    }
                    QPushButton:hover {
                        background-color: #1abc9c;
                    }
                    QPushButton:pressed {
                        background-color: #1e88e5;
                    }
                """)
        toggle_laser.clicked.connect(self.toggle_laser)

        controls_layout.addWidget(self.led_status)
        controls_layout.addWidget(self.laser_status)
        controls_layout.addWidget(toggle_led)
        controls_layout.addWidget(toggle_laser)

        top_layout.addLayout(controls_layout)
        main_layout.addLayout(top_layout)

        # ===== INFOS DU BAS =====
        bottom_layout = QHBoxLayout()

        # -------- COLONNE GAUCHE : Infos --------
        info_col = QVBoxLayout()
        info_col.setSpacing(15)

        info_title = QLabel("🔍 Informations Système")
        info_title.setStyleSheet("padding: 12px; font-size: 18px; font-weight: bold;")
        info_col.addWidget(info_title, alignment=Qt.AlignLeft)

        self.temp_label = QLabel("🌡️ Température : 0.0 °C")
        self.inclination_label = QLabel("🧭 Inclinaison : Pitch 0.0° | Roll 0.0°")

        for label in [self.temp_label, self.inclination_label]:
            label.setStyleSheet("""
                padding: 12px;
                font-size: 18px;
                background-color: #34495e;
                color: white;
                border-radius: 12px;
                margin-bottom: 15px;
                font-weight: bold;
            """)
            label.setAlignment(Qt.AlignLeft)

        info_col.addWidget(self.temp_label)
        info_col.addWidget(self.inclination_label)

        # -------- SÉPARATEUR VERTICAL --------
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setStyleSheet("color: #7f8c8d;")
        separator1.setLineWidth(1)

        # -------- COLONNE DROITE : Batterie + Modèle 3D --------
        right_col = QVBoxLayout()

        battery_label = QLabel("🔋 Batterie")
        battery_label.setStyleSheet("margin-bottom: 10px; font-size: 14px; color: #ecf0f1;")
        self.battery_bar = QProgressBar()
        self.battery_bar.setOrientation(Qt.Horizontal)
        self.battery_bar.setValue(0)
        self.battery_bar.setFixedSize(300, 25)
        self.battery_bar.setTextVisible(True)
        self.battery_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                background-color: #1e2b3a;
                font-size: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
                width: 8px;
                margin: 1px;
            }
        """)

        self.model_3d_widget = gl.GLViewWidget()
        self.model_3d_widget.setFixedSize(400, 200)
        self.model_3d_widget.setCameraPosition(distance=15)
        # Corps du drone (cube)
        body_length = 3
        body_width = 3
        body_height = 1

        verts = np.array([
            [body_length / 2, body_width / 2, 0],
            [-body_length / 2, body_width / 2, 0],
            [-body_length / 2, -body_width / 2, 0],
            [body_length / 2, -body_width / 2, 0],
            [body_length / 2, body_width / 2, body_height],
            [-body_length / 2, body_width / 2, body_height],
            [-body_length / 2, -body_width / 2, body_height],
            [body_length / 2, -body_width / 2, body_height]
        ])

        faces = np.array([
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4],
            [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6],
            [3, 0, 4], [3, 4, 7]
        ])

        colors = np.array([[0.2, 0.6, 0.8, 1]] * len(faces))  # Bleu clair

        self.drone_body = gl.GLMeshItem(vertexes=verts, faces=faces, faceColors=colors, smooth=False, drawEdges=True,
                                        edgeColor=(1, 1, 1, 1))
        self.model_3d_widget.addItem(self.drone_body)

        right_col.addWidget(self.model_3d_widget)

        right_col.addWidget(battery_label)
        right_col.addWidget(self.battery_bar, alignment=Qt.AlignLeft)
        right_col.addSpacing(10)

        bottom_layout.addLayout(info_col)
        bottom_layout.addWidget(separator1)
        bottom_layout.addLayout(right_col)

        main_layout.addLayout(bottom_layout)

        # 🎥 Webcam
        self.cap = cv2.VideoCapture(1)

        # ⏱️ Timer pour mise à jour
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_interface)
        self.timer.start(100)

    def toggle_led(self):
        # Inverser l'état de la LED
        self.etat_led = 1 - self.etat_led
        # Mettre à jour le texte
        self.led_status.setText("💡 LED : ON" if self.etat_led else "💡 LED : OFF")
        # Envoyer l'état mis à jour
        y_gauche, rt, lt, bouton_a, bouton_b = lire_commandes()
        envoyer_donnees(y_gauche, rt, lt, self.etat_laser, self.etat_led)

    def toggle_laser(self):
        # Inverser l'état du laser
        self.etat_laser = 1 - self.etat_laser
        # Mettre à jour le texte
        self.laser_status.setText("🔦 Laser : ON" if self.etat_laser else "🔦 Laser : OFF")
        # Envoyer l'état mis à jour
        y_gauche, rt, lt, bouton_a, r = lire_commandes()
        envoyer_donnees(y_gauche, rt, lt, self.etat_laser, self.etat_led)

    def lire_donnees(self):
        if ser.in_waiting:
            data_recue = ser.readline().decode('utf-8', errors='ignore').strip()
            if data_recue:
                parts = data_recue.split('|')
                if len(parts) >= 4:
                    temp = parts[0].split(':')[1].strip().replace('C', '')
                    x = parts[1].split(':')[1].strip().replace('mg', '')
                    y = parts[2].split(':')[1].strip().replace('mg', '')
                    z = parts[3].split(':')[1].strip().replace('mg', '')

                    if x and y and z:
                        x = float(x)
                        y = float(y)
                        z = float(z)

                        roll = np.arctan2(y, z) * (180 / np.pi)
                        pitch = np.arctan2(-x, np.sqrt(y**2 + z**2)) * (180 / np.pi)

                        self.temperature = float(temp)
                        self.pitch = pitch
                        self.roll = roll

    def zoom_in(self):
        if self.zoom_factor < 2.0:
            self.zoom_factor += 0.1

    def zoom_out(self):
        if self.zoom_factor > 0.5:
            self.zoom_factor -= 0.1

    def toggle_recording(self):
        self.recording = not self.recording
        if self.recording:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop", "bubble_record.avi")
            self.video_writer = cv2.VideoWriter(desktop_path, fourcc, 20.0, (800, 400))
            self.record_button.setText("⏹️ Arrêter l'enregistrement")
        else:
            self.video_writer.release()
            self.video_writer = None
            self.record_button.setText("⏺️ Démarrer l'enregistrement")

    def update_interface(self):
        # 🎥 Mise à jour caméra
        ret, frame = self.cap.read()
        if ret:
            h, w, _ = frame.shape
            center_x, center_y = w // 2, h // 2
            zoom_w, zoom_h = int(w / self.zoom_factor), int(h / self.zoom_factor)
            x1 = max(center_x - zoom_w // 2, 0)
            y1 = max(center_y - zoom_h // 2, 0)
            x2 = min(center_x + zoom_w // 2, w)
            y2 = min(center_y + zoom_h // 2, h)
            zoomed_frame = frame[y1:y2, x1:x2]
            zoomed_frame = cv2.resize(zoomed_frame, (800, 400))

            if self.recording and self.video_writer:
                self.video_writer.write(zoomed_frame)

            rgb_image = cv2.cvtColor(zoomed_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.camera_view.setPixmap(QPixmap.fromImage(image))

        # 🔋 Mise à jour batterie
        battery = psutil.sensors_battery()
        if battery:
            self.battery_bar.setValue(battery.percent)

        y_gauche, rt, lt, bouton_a, bouton_b = lire_commandes()

        # Faire tourner le modèle 3D selon le pitch et roll
        self.drone_body.resetTransform()
        self.drone_body.rotate(self.roll, 0, 0, 1)  # Roll autour de Z
        self.drone_body.rotate(self.pitch, 1, 0, 0)  # Pitch autour de X
        # Toggle LASER
        if bouton_a == 1 and self.etat_precedent_bouton_a == 0:
            self.etat_laser = 1 - self.etat_laser  # Inverse l'état de la Laser
            self.laser_status.setText("🔦 Laser : ON" if self.etat_laser else "🔦 Laser : OFF")

        self.etat_precedent_bouton_a = bouton_a  # Mémorise l'état actuel du bouton
        # Toggle Led
        if bouton_b == 1 and self.etat_precedent_bouton_b == 0:
            self.etat_led = 1 - self.etat_led  # Inverse l'état de la LED
            self.led_status.setText("💡 LED : ON" if self.etat_led else "💡 LED : OFF")

        self.etat_precedent_bouton_b = bouton_b  # Mémorise l'état actuel du bouton

        # Envoyer les données série
        envoyer_donnees(y_gauche, rt, lt, self.etat_laser, self.etat_led)
        time.sleep(0.1)

        # 🔥 Mise à jour des labels
        self.temp_label.setText(f"🌡️ Température : {self.temperature:.1f} °C")
        self.inclination_label.setText(f"🧭 Inclinaison : Pitch {self.pitch:.1f}° | Roll {self.roll:.1f}°")

        # 🔎 Lecture des données série
        self.lire_donnees()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    dashboard = BubbleDashboard()
    dashboard.show()
    sys.exit(app.exec_())

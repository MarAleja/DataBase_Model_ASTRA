"""Pisos, modelos candidatos y validacion justa (dejando una sesion fuera).

Validacion: en cada vuelta se entrena con todas las sesiones de entrenamiento
menos una, y se prueba en la que quedo fuera (electrodos recolocados). Es la
misma situacion que la prueba final con electrodos nuevos. Nunca se mezclan
ventanas de una misma sesion entre entrenar y probar.

Pisos (diapositiva 10 del curso):
  azar     siempre dice la clase mas comun del entrenamiento (~50 % con clases iguales)
  umbral   un solo numero sobre el RMS, sin machine learning
"""
import json
import subprocess
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .caracteristicas import NOMBRES


class UmbralUnaCaracteristica(BaseEstimator, ClassifierMixin):
    """'Movimiento si la caracteristica pasa este numero'. Usa la columna 0."""

    def fit(self, X, y):
        x = np.asarray(X, dtype=float)[:, 0]
        y = np.asarray(y)
        candidatos = np.unique(np.quantile(x, np.linspace(0.01, 0.99, 197)))
        mejor = (-1.0, 0.0, 1)
        for t in candidatos:
            for signo in (1, -1):                      # por si arriba diera menos que reposo
                acc = np.mean(((signo * (x - t)) > 0).astype(int) == y)
                if acc > mejor[0]:
                    mejor = (acc, t, signo)
        _, self.umbral_, self.signo_ = mejor
        self.classes_ = np.array([0, 1])
        return self

    def predict(self, X):
        x = np.asarray(X, dtype=float)[:, 0]
        return ((self.signo_ * (x - self.umbral_)) > 0).astype(int)


def candidatos():
    """{nombre: (estimador, columnas)} del mas simple al mas flexible."""
    todas = list(NOMBRES)
    return {
        "chance floor": (DummyClassifier(strategy="most_frequent"), ["rms"]),
        "threshold floor (RMS)": (UmbralUnaCaracteristica(), ["rms"]),
        "logistic regression (RMS)": (make_pipeline(StandardScaler(), LogisticRegression()),
                                      ["rms"]),
        "logistic regression (6 features)": (make_pipeline(StandardScaler(),
                                                           LogisticRegression(max_iter=1000)),
                                             todas),
        "k nearest neighbours, k=5 (6 features)": (make_pipeline(StandardScaler(),
                                                                 KNeighborsClassifier(5)), todas),
        "decision tree, depth 3 (6 features)": (DecisionTreeClassifier(max_depth=3,
                                                                       random_state=0), todas),
    }


def validar_por_sesion(tabla, modelos=None):
    """Deja una sesion fuera en cada vuelta. Regresa (resumen, por_sesion, confusiones)."""
    modelos = modelos or candidatos()
    grupos = tabla["session"].to_numpy()
    y = tabla["label"].to_numpy()
    filas, confusiones = [], {}
    for nombre, (est, cols) in modelos.items():
        X = tabla[cols].to_numpy(dtype=float)
        cm = np.zeros((2, 2), dtype=int)
        for tr, te in LeaveOneGroupOut().split(X, y, grupos):
            est.fit(X[tr], y[tr])
            pred = est.predict(X[te])
            cm += confusion_matrix(y[te], pred, labels=[0, 1])
            filas.append({"model": nombre, "held_out_session": grupos[te][0],
                          "accuracy": accuracy_score(y[te], pred)})
        confusiones[nombre] = cm
    por_sesion = pd.DataFrame(filas)
    resumen = (por_sesion.groupby("model", sort=False)["accuracy"]
               .agg(["mean", "std", "min"]).reset_index())
    return resumen, por_sesion, confusiones


def entrenar_final(tabla, nombre):
    """Entrena el modelo elegido con TODAS las sesiones de entrenamiento."""
    est, cols = candidatos()[nombre]
    est.fit(tabla[cols].to_numpy(dtype=float), tabla["label"].to_numpy())
    return est, cols


def commit_actual(raiz):
    try:
        return subprocess.run(["git", "-C", str(raiz), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def guardar(est, cols, nombre, resumen_cv, n_ventanas, ruta_joblib, ruta_json, raiz):
    """Guarda el modelo (joblib) y una ficha legible (json) con su version."""
    import joblib
    joblib.dump({"model": est, "features": cols, "name": nombre}, ruta_joblib)
    fila = resumen_cv[resumen_cv["model"] == nombre].iloc[0]
    ficha = {"name": nombre, "features": cols, "classes": {"0": "rest", "1": "neck up"},
             "window_ms": 100, "cv_accuracy_mean": round(float(fila["mean"]), 4),
             "cv_accuracy_min": round(float(fila["min"]), 4), "training_windows": int(n_ventanas),
             "trained_at": datetime.now().isoformat(timespec="seconds"),
             "git_commit": commit_actual(raiz)}
    if hasattr(est, "umbral_"):
        ficha["threshold"] = float(est.umbral_)
    ruta_json.write_text(json.dumps(ficha, indent=2), encoding="utf-8")
    return ficha

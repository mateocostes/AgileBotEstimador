# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

from email import message
from pickle import FALSE
import string
from tkinter import N
from tokenize import Double
from typing import Any, Text, Dict, List
from numpy import double, integer
#
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
from datetime import datetime
import json
import random
import requests
from flask import jsonify
from datetime import datetime

from sqlalchemy import case, false, true

tarea = None

#
#

def readArchivo(dire)-> dict:
        with open(dire,"r") as archivo:
            diccionario = json.loads(archivo.read()) 
            archivo.close()
        return diccionario

def writeArchivo(dire,diccionario):
        with open(dire,"w") as archivo:
            json.dump(diccionario,archivo)
            archivo.close()

api_endpoint_set_vector = "http://IP/dispatcher/set-vector"
api_endpoint_get_vector = "http://IP/dispatcher/get-vector"
diccionarioParticipantes = ""
direcDatos = "actions/motivo.json"
diccionarioDatos = readArchivo(direcDatos) #Ya no se lee aca, se siempre que se usa el diccionario por si se actualiza en tiempo de ejecucion

def existeParticipante(nombre_participante) -> bool:
    response = requests.get(url=api_endpoint_get_vector).text
    #print("response: " + response)
    diccionarioParticipantes = json.loads(response)
    for participante in diccionarioParticipantes:
        if (participante["nickname"] == nombre_participante):
            return True
    return False

class ActionGuardarNombre(Action):

    def name(self) -> Text:
        return "guardar_nombre"
    
    def obtenerSaludoHora() -> Text:
        hora_actual = datetime.now().hour
        if hora_actual >= 6 and hora_actual < 12:
            return "Buenos días"
        elif hora_actual >= 12 and hora_actual < 18:
            return "Buenas tardes"
        else:
            return "Buenas noches"  
    
    def generarIntroduccion(self, nombre_partipante) -> Text:
        #Se generan distintas introducciones que el chatbot mencionara.
        lista_introduccion = []
        introduccion = f"{self.obtenerSaludoHora} {nombre_partipante}"
        ejemplo1 = f"{introduccion}, puedo ayudarte en estimar una tarea o mencionarte la persona mas indicada para la misma, consultame!"
        ejemplo2 = f"{introduccion}, estoy aqui para ayudarte. Puedes consultarme acerca de la estimacion de tareas o preguntarme quien es la persona mas indicada para realizar una tarea especifica."
        ejemplo3 = f"{introduccion}, si necesitas estimar el tiempo necesario para completar una tarea o encontrar a la persona adecuada para realizarla, puedo ayudarte!"
        ejemplo4 = f"{introduccion}, mi objetivo es brindarte asistencia en la estimación de tareas y en la identificacion de la persona más idonea para llevarlas a cabo. No dudes en preguntarme!"
        ejemplo5 = f"{introduccion}, contame sobre la tarea que necesitas estimar o la persona que buscas para llevarla a cabo, para poder brindarte la informacion que necesitas."
        ejemplo6 = f"{introduccion}, puedo proporcionarte estimaciones precisas y recomendaciones sobre quién deberia encargarse de determinadas tareas. Preguntame lo que necesites!"
        lista_introduccion.append(ejemplo1)
        lista_introduccion.append(ejemplo2)
        lista_introduccion.append(ejemplo3)
        lista_introduccion.append(ejemplo4)
        lista_introduccion.append(ejemplo5)
        lista_introduccion.append(ejemplo6)
        return random.choice(lista_introduccion)

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        nombre_partipante = next (tracker.get_latest_entity_values("participante"),None)
        message = ""
        if (nombre_partipante != None):
            print("Nombre partipante reconocido: " + str(nombre_partipante))
            if(existeParticipante(nombre_partipante)):
                message = self.generarIntroduccion(nombre_partipante)
                dispatcher.utter_message(text=message)
            else:
                message = "El nombre no corresponde a un AgileBot perteneciente al mundo"
                dispatcher.utter_message(text=message)
        else:
            message = "No se puede reconocer el nombre del AgileBot"
            dispatcher.utter_message(text=message)
        return [SlotSet("participante",str(nombre_partipante))]
    

def asignarTarea(tracker)-> bool:
    #Obtengo la tarea de la entidad, en caso de no cargarse, la obtengo del slot. En caso contrario retorno false.
    global tarea
    tarea = next (tracker.get_latest_entity_values("tarea"),None)
    if (tarea != None):
            return true
    else:
        tarea = str(tracker.get_slot("participante"))
        if (tarea != None):
            return true
        else: return false
    
class ActionDarMotimoEstimacion(Action):

    def name(self) -> Text:
        return "dar_motivo_estimacion"

    def aproximarVotoEstimacion(self, valor) -> int:
        lista_votos = [0, 0.5, 1, 2, 3, 5, 8, 20, 40, 100, 1000] #No puedo usar la definida al principio porque es de strings.
        voto_aproximado = min(lista_votos, key=lambda v: abs(v - valor)) #La función lambda calcula la distancia absoluta entre cada voto v y valor, y min() encuentra el voto con la distancia mínima.
        return voto_aproximado
    
    def generarMotivoEstimacion(self) -> Text:
        global tarea
        motivo = ""
        if diccionarioDatos["tareas_similares"][0] == "":
            motivo = "No hay datos suficientes para estimar la tarea mencionada."
        elif diccionarioDatos["tareas_similares"][0] == tarea:
            autor_tarea = diccionarioDatos["tareas_similares"][0]["autor"]
            estimacion = diccionarioDatos["tareas_similares"][0]["estimacion"]
            motivo = f"La tarea ingresada ya fue realizada anteriormente por {autor_tarea}, con una estimacion de {estimacion} puntos."
        else:
            tarea_similar1 = diccionarioDatos["tareas_similares"][0]["tarea"]
            estimacion_tarea_similar1 = diccionarioDatos["tareas_similares"][0]["estimacion"]
            autor_tarea_similar1 = diccionarioDatos["tareas_similares"][0]["autor"]
            motivo_tarea_similar1 = f"{tarea_similar1} con una estimacion de {estimacion_tarea_similar1} puntos, realizada por {autor_tarea_similar1}"
            if diccionarioDatos["tareas_similares"][1] != "":
                tarea_similar2 = diccionarioDatos["tareas_similares"][1]["tarea"]
                estimacion_tarea_similar2 = diccionarioDatos["tareas_similares"][1]["estimacion"]
                autor_tarea_similar2 = diccionarioDatos["tareas_similares"][0]["autor"]
                motivo_tarea_similar2 = f"{tarea_similar2} con una estimacion de {estimacion_tarea_similar2} puntos, realizada por {autor_tarea_similar2}"
                motivo = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar1} y {motivo_tarea_similar2}"
            else:
                motivo = f"Basandome en la tareas realizada anteriormente {motivo_tarea_similar1}"
            estimacion = self.aproximarVotoEstimacion(diccionarioDatos["promedio"])
            motivo = f"{motivo}, me parece correcto que la tarea se estime con un puntaje de {estimacion}"
        

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = ""
        if asignarTarea(tracker):
            message = self.generarMotivoEstimacion()
        else:
            message = "Debe indicarme la tarea a la cual desea estimar"
        dispatcher.utter_message(text=message)
        return [SlotSet("tarea",str(tarea))]





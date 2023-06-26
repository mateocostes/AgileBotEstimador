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

tarea = ""
motivoEstimacion = ""
motivoPersona = ""
estimacionHora = 8 #Constante utilizada para determinar cuando vale un punto es relacion a horas. En nuestro caso 1 punto vale 8 horas.
diccionarioDatos = ""

def readArchivo(dire)-> dict:
    with open(dire,"r") as archivo:
        diccionario = json.loads(archivo.read()) 
        archivo.close()
    return diccionario

def writeArchivo(dire,diccionario):
    with open(dire,"w") as archivo:
        json.dump(diccionario,archivo)
        archivo.close()

ip = "56e0-201-235-167-187.ngrok-free.app" #MODIFICAR
api_endpoint_get_recomendacion = f"http://{ip}/dispatcher/get-recomendacion"
api_endpoint_get_vector = f"http://{ip}/dispatcher/get-vector"
diccionarioParticipantes = ""

def existeParticipante(nombre_participante) -> bool:
    response = requests.get(url=api_endpoint_get_vector).text
    diccionarioParticipantes = json.loads(response)
    for participante in diccionarioParticipantes:
        if (participante["nickname"] == nombre_participante):
            return True
    return False

class ActionGuardarNombre(Action):

    def name(self) -> Text:
        return "guardar_nombre"
    
    def obtenerSaludoHora(self) -> Text:
        hora_actual = datetime.now().hour
        if hora_actual >= 1 and hora_actual < 12:
            return "Buenos dias"
        elif hora_actual >= 12 and hora_actual < 20:
            return "Buenas tardes"
        else:
            return "Buenas noches"  
    
    def generarIntroduccion(self, nombre_partipante) -> Text:
        #Se generan distintas introducciones que el chatbot mencionara.
        lista_introduccion = []
        introduccion = f"{self.obtenerSaludoHora()} {nombre_partipante}"
        ejemplo1 = f"{introduccion}, puedo ayudarte en estimar una tarea o mencionarte la persona mas indicada para la misma. Consultame lo que necesites!"
        ejemplo2 = f"{introduccion}, estoy aqui para ayudarte. Podes consultarme acerca de la estimacion de tareas o preguntarme quien es la persona mas indicada para realizar una tarea especifica."
        ejemplo3 = f"{introduccion}, si necesitas estimar el tiempo necesario para completar una tarea o encontrar a la persona adecuada para realizarla, puedo ayudarte!"
        ejemplo4 = f"{introduccion}, mi objetivo es brindarte asistencia en la estimacion de tareas y en la identificacion de la persona mas idonea para llevarlas a cabo. No dudes en preguntarme!"
        ejemplo5 = f"{introduccion}, contame sobre la tarea que necesitas estimar o la persona que buscas para llevarla a cabo, para poder brindarte la informacion que necesitas."
        ejemplo6 = f"{introduccion}, puedo proporcionarte estimaciones precisas y recomendaciones sobre quien deberia encargarse de determinadas tareas. Preguntame lo que necesites!"
        lista_introduccion.append(ejemplo1)
        lista_introduccion.append(ejemplo2)
        lista_introduccion.append(ejemplo3)
        lista_introduccion.append(ejemplo4)
        lista_introduccion.append(ejemplo5)
        lista_introduccion.append(ejemplo6)
        return random.choice(lista_introduccion)
    
    def reinicializarVariablesGlobales(self):
        global tarea, motivoEstimacion, motivoPersona
        tarea = ""
        motivoEstimacion = ""
        motivoPersona = ""

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        nombre_partipante = next (tracker.get_latest_entity_values("participante"),None)
        message = ""
        if (nombre_partipante != None):
            print("Nombre partipante reconocido: " + str(nombre_partipante))
            self.reinicializarVariablesGlobales()
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
    
def AsignarJsonDatos():
    global diccionarioDatos, tarea
    print("tarea get: " + str(tarea))
    response = requests.post(url=api_endpoint_get_recomendacion, json= {"tarea": tarea}).text
    diccionarioDatos = ""
    diccionarioDatos = json.loads(response)
    print("diccionarioDatos: " + str(diccionarioDatos))

def asignarTarea(tracker)-> int:
    #Obtengo la tarea de la entidad, en caso de no cargarse, la obtengo del slot. En caso contrario retorno False.
    global tarea
    tarea = next(tracker.get_latest_entity_values("tarea"),None)
    if (tarea != None):
        return 0 #Retorna 0 porque tarea no es None y porque lo reconocio como entidad
    else:
        tarea = tracker.get_slot("tarea")
        if (tarea != None):
            return 1 #Retorna 1 porque tarea no es None y porque lo reconocio como slot
        else: 
            return -1 #Retorna -1 porque tarea es None y porque no lo reconocio
        
def seleccionarHistoricos(valor_maximo):
    valores = random.sample(range(valor_maximo), 2)
    return valores[0], valores[1]
    
def leerDatosHistoricos(posicion, tarea, ejecutor, puntos):
    if len(diccionarioDatos["historicos"]) > posicion: #Si tiene algun valor cargado
        tarea = diccionarioDatos["historicos"][posicion]["tarea"]
        ejecutor = diccionarioDatos["historicos"][posicion]["ejecutor"]
        puntos = diccionarioDatos["historicos"][posicion]["puntos"]
    return tarea, ejecutor, puntos

def generarMotivos(tracker):
    global tarea, diccionarioDatos, motivoEstimacion, motivoPersona
    #Inicializo variables
    motivoEstimacion == ""
    motivoPersona == ""
    historico_tarea = ""
    historico_ejecutor = ""
    historico_puntos =""
    lista_comparacionPersonas = []
    lista_motivosEstimacion = []
    lista_motivosPersona = []
    participante = tracker.get_slot("participante")

    historico_tarea, historico_ejecutor, historico_puntos = leerDatosHistoricos(0, historico_tarea, historico_ejecutor, historico_puntos)
    if historico_tarea == None and historico_ejecutor == None and historico_puntos == None: #Si no hay datos
        motivoEstimacion1 = "No hay datos suficientes para estimar la tarea mencionada."
        motivoEstimacion2 = "No se dispone de informacion necesaria para estimar la duracion de la tarea."
        motivoEstimacion3 = "La falta de datos impide realizar una estimacion precisa para la tarea mencionada."
        motivoEstimacion4 = "No se puede calcular la duracion estimada debido a la falta de datos pertinentes."
        motivoEstimacion5 = "La ausencia de informacion adecuada dificulta la estimacion de la tarea en cuestion."

        motivoPersona1 = "No hay datos suficientes para recomendar a alguien a la tarea mencionada."
        motivoPersona2 = "La falta de informacion impide realizar una recomendacion adecuada para la tarea mencionada."
        motivoPersona3 = "No se dispone de datos suficientes para recomendar a alguien para la tarea mencionada."
        motivoPersona4 = "La tarea mencionada carece de informacion necesaria para hacer una recomendacion."
        motivoPersona5 = "La falta de datos pertinentes dificulta la recomendacion de alguien para la tarea mencionada."

    elif historico_tarea == tarea: #Si la tarea ya fue realizada
        if (participante != None) and (participante == historico_ejecutor): #Si la persona que realiza la pregunta es la que realizo la tarea, dice usted en vez de su nombre
            historico_ejecutor = "usted"
        
        motivoEstimacion1 = f"La tarea ingresada ya fue realizada anteriormente por {historico_ejecutor}, con una demora de {historico_puntos} puntos, es decir {historico_puntos * estimacionHora} horas."
        motivoEstimacion2 = f"La solicitud de trabajo coincide con una tarea previa realizada por {historico_ejecutor}, quien tardo {historico_puntos} puntos, lo equivalente a {historico_puntos * estimacionHora} horas, en completarla."
        motivoEstimacion3 = f"Segun los registros, {historico_ejecutor} ya ha abordado esa tarea y demoro {historico_puntos} puntos para completarla, es decir {historico_puntos * estimacionHora} horas."
        motivoEstimacion4 = f"Esta tarea ya fue anteriormente realizada por {historico_ejecutor}, quien se retardo {historico_puntos} puntos, lo equivalente a {historico_puntos * estimacionHora} horas, para su finalizacion."
        motivoEstimacion5 = f"El solicitante {historico_ejecutor} ya ha llevado a cabo una tarea identica, tardando alrededor de {historico_puntos} puntos para finalizarla, lo equivalente a {historico_puntos * estimacionHora} horas."

        motivoPersona1 = f"Recomiendo a {historico_ejecutor}, ya que realizo la tarea ingresada anteriormente, tardando {historico_puntos} puntos, es decir {historico_puntos * estimacionHora} horas."
        motivoPersona2 = f"Te sugiero a {historico_ejecutor} para esta tarea, ya que ha completado exitosamente el trabajo previo en un tiempo de {historico_puntos} puntos, lo equivalente a {historico_puntos * estimacionHora} horas."
        motivoPersona3 = f"Basado en el historial de ejecucion, te recomiendo encarecidamente a {historico_ejecutor}. En la tarea anterior, demostro su experiencia al finalizarla con una estimacion precisa de {historico_puntos} puntos, es decir {historico_puntos * estimacionHora} horas."
        motivoPersona4 = f"Para esta tarea, te recomendaria a {historico_ejecutor} sin dudarlo. En la ocasion anterior, demostro un alto nivel de dedicacion y esfuerzo, completando la tarea en {historico_puntos} puntos, lo equivalente a {historico_puntos * estimacionHora} horas."
        motivoPersona5 = f"Mi recomendacion es asignar a {historico_ejecutor} para esta tarea. En la tarea anterior, mostro habilidades excepcionales y logro completarla con exito en tan solo {historico_puntos} puntos, lo equivalente a {historico_puntos * estimacionHora} horas."
    else:
        estimacion = diccionarioDatos["promedio_puntos"]
        if len(diccionarioDatos["historicos"]) > 1:
            #Se eligen dos historicos aleatorios del total
            pos1, pos2 = seleccionarHistoricos(len(diccionarioDatos["historicos"]))
            historico_tarea1 = ""
            historico_ejecutor1 = ""
            historico_puntos1 = ""
            historico_tarea2 = ""
            historico_ejecutor2 = ""
            historico_puntos2 = ""
            motivo_tarea_similar = ""
            historico_tarea1, historico_ejecutor1, historico_puntos1 = leerDatosHistoricos(pos1, historico_tarea1, historico_ejecutor1, historico_puntos1)
            historico_tarea2, historico_ejecutor2, historico_puntos2 = leerDatosHistoricos(pos2, historico_tarea2, historico_ejecutor2, historico_puntos2)

            if (participante != None): #Si la persona que realiza la pregunta es la que realizo la tarea, dice usted en vez de su nombre
                if (participante == historico_ejecutor1):
                    historico_ejecutor1 = "usted"
                if (participante == historico_ejecutor2):
                    historico_ejecutor2 = "usted"

            if historico_ejecutor1 != historico_ejecutor2: #Si las tareas fueron realizadas por personas diferentes
                motivo_tarea_similar = f"{historico_tarea1} con una estimacion de {historico_puntos1} puntos, realizada por {historico_ejecutor1}"
                if historico_tarea2[0].lower() == 'i': #si la primera letra es "i"
                    motivo_tarea_similar = f"{motivo_tarea_similar} e {historico_tarea2} con una estimacion de {historico_puntos2} puntos, realizada por {historico_ejecutor2}"
                else:
                    motivo_tarea_similar = f"{motivo_tarea_similar} y {historico_tarea2} con una estimacion de {historico_puntos2} puntos, realizada por {historico_ejecutor2}"

                motivoPersona1 = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar}, tanto {historico_ejecutor1} como {historico_ejecutor2}, podrian resolver perfectamente la nueva tarea."
                motivoPersona2 = f"Considerando el historial de tareas previas, como {motivo_tarea_similar}, tanto {historico_ejecutor1} como {historico_ejecutor2} demostraron habilidades sobresalientes y podrian resolver perfectamente la nueva tarea."
                motivoPersona3 = f"Tomando como referencia trabajos similares previamente completados, como {motivo_tarea_similar}, tanto {historico_ejecutor1} como {historico_ejecutor2} han demostrado competencia y podrian abordar con exito la nueva tarea."
                motivoPersona4 = f"Basandome en el desempeño en tareas anteriores, como {motivo_tarea_similar}, tanto {historico_ejecutor1} como {historico_ejecutor2} se destacaron por su eficiencia y podrian resolver perfectamente la nueva tarea."
                motivoPersona5 = f"Al analizar tareas similares realizadas en el pasado, como {motivo_tarea_similar}, tanto {historico_ejecutor1} como {historico_ejecutor2} han demostrado habilidades excepcionales y podrian abordar la nueva tarea con exito."
            else: #Si las tareas fueron realizadas por la misma persona
                motivo_tarea_similar = f"{historico_tarea1} con una estimacion de {historico_puntos1} puntos"
                if historico_tarea2[0].lower() == 'i': #si la primera letra es "i"
                    motivo_tarea_similar = f"{motivo_tarea_similar} e {historico_tarea2} con una estimacion de {historico_puntos2} puntos, ambas realizadas por {historico_ejecutor2}"
                else:
                    motivo_tarea_similar = f"{motivo_tarea_similar} y {historico_tarea2} con una estimacion de {historico_puntos2} puntos, ambas realizadas por {historico_ejecutor2}"

                motivoPersona1 = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar}, el mismo, podria resolver perfectamente la nueva tarea."
                motivoPersona2 = f"Considerando el historial de tareas previas, como {motivo_tarea_similar}, demostrando habilidades sobresalientes, podria resolver perfectamente la nueva tarea."
                motivoPersona3 = f"Tomando como referencia trabajos similares previamente completados, como {motivo_tarea_similar}, demostrando competencia, podria abordar con exito la nueva tarea."
                motivoPersona4 = f"Basandome en el desempeño en tareas anteriores, como {motivo_tarea_similar}, destacandose por su eficiencia, el mismo, podria resolver perfectamente la nueva tarea."
                motivoPersona5 = f"Al analizar tareas similares realizadas en el pasado, como {motivo_tarea_similar}, habiendo demostrado habilidades excepcionales, podria abordar la nueva tarea con exito."

            motivoEstimacion1 = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar}, me parece correcto que la nueva tarea se estime con un puntaje de {estimacion}"
            motivoEstimacion2 = f"Considerando el historial de tareas previas, como {motivo_tarea_similar}, propongo estimar la nueva tarea con {estimacion} puntos."
            motivoEstimacion3 = f"Tomando como referencia trabajos similares previamente completados, como {motivo_tarea_similar}, sugiero una estimacion de {estimacion} puntos para la tarea actual."
            motivoEstimacion4 = f"Basandome en el desempeño en tareas anteriores, como {motivo_tarea_similar}, creo que una estimacion de {estimacion} puntos seria apropiada para la nueva tarea."
            motivoEstimacion5 = f"Al analizar tareas similares realizadas en el pasado, como {motivo_tarea_similar}, considero razonable asignar una estimacion de {estimacion} puntos a la tarea actual."

            if historico_puntos1 != historico_puntos2 and historico_ejecutor1 != historico_ejecutor2:
                if historico_puntos1 > historico_puntos2: #Si una persona resolvio mas rapido una tarea que otra.
                    motivoComparacionPersonas1 = f"Aunque ambos ejecutores son competentes, me inclino a recomendar a {historico_ejecutor1} debido a su desempeño notablemente mas rapido en tareas similares anteriores. Su eficiencia demostrada podria garantizar una entrega oportuna de la nueva tarea."
                    motivoComparacionPersonas2 = f"Sin embargo, mi recomendacion principal es {historico_ejecutor1}, ya que demostro ser mas eficiente en el tiempo empleado."
                    motivoComparacionPersonas3 = f"No obstante, te sugiero especialmente a {historico_ejecutor1}, quien completo la tarea en un tiempo menor, mostrando una mayor capacidad de entrega."
                    motivoComparacionPersonas4 = f"A pesar de eso, mi preferencia recae en {historico_ejecutor1}, ya que ha demostrado un rendimiento mas rapido y efectivo en tareas similares anteriores."
                    motivoComparacionPersonas5 = f"Sin embargo, mi recomendacion principal es asignar la tarea a {historico_ejecutor1}, quien logro terminarla en menos tiempo, lo que indica una mayor eficiencia en su trabajo."
                else:
                    motivoComparacionPersonas1 = f"Aunque ambos ejecutores son competentes, me inclino a recomendar a {historico_ejecutor2} debido a su desempeño notablemente mas rapido en tareas similares anteriores. Su eficiencia demostrada podria garantizar una entrega oportuna de la nueva tarea."
                    motivoComparacionPersonas2 = f"Sin embargo, mi recomendacion principal es {historico_ejecutor2}, ya que demostro ser mas eficiente en el tiempo empleado."
                    motivoComparacionPersonas3 = f"No obstante, te sugiero especialmente a {historico_ejecutor2}, quien completo la tarea en un tiempo menor, mostrando una mayor capacidad de entrega."
                    motivoComparacionPersonas4 = f"A pesar de eso, mi preferencia recae en {historico_ejecutor2}, ya que ha demostrado un rendimiento mas rapido y efectivo en tareas similares anteriores."
                    motivoComparacionPersonas5 = f"Sin embargo, mi recomendacion principal es asignar la tarea a {historico_ejecutor2}, quien logro terminarla en menos tiempo, lo que indica una mayor eficiencia en su trabajo."
                
                lista_comparacionPersonas = [motivoComparacionPersonas1, motivoComparacionPersonas2, motivoComparacionPersonas3, motivoComparacionPersonas4, motivoComparacionPersonas5]
                motivoComparacionPersonas =  random.choice(lista_comparacionPersonas)
                motivoPersona1 = f"{motivoPersona1} {motivoComparacionPersonas}"
                motivoPersona2 = f"{motivoPersona2} {motivoComparacionPersonas}"
                motivoPersona3 = f"{motivoPersona3} {motivoComparacionPersonas}"
                motivoPersona4 = f"{motivoPersona4} {motivoComparacionPersonas}"
                motivoPersona5 = f"{motivoPersona5} {motivoComparacionPersonas}"
        else:
            motivo_tarea_similar = f"{historico_tarea} con una estimacion de {historico_puntos} puntos, realizada por {historico_ejecutor}"
            motivoEstimacion1 = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar}, me parece correcto que la nueva tarea se estime con un puntaje de {estimacion}"
            motivoEstimacion2 = f"Considerando el historial de tareas previas, como {motivo_tarea_similar}, propongo estimar la nueva tarea con {estimacion} puntos."
            motivoEstimacion3 = f"Tomando como referencia trabajos similares previamente completados, como {motivo_tarea_similar}, sugiero una estimacion de {estimacion} puntos para la tarea actual."
            motivoEstimacion4 = f"Basandome en el desempeño en tareas anteriores, como {motivo_tarea_similar}, creo que una estimacion de {estimacion} puntos seria apropiada para la nueva tarea."
            motivoEstimacion5 = f"Al analizar tareas similares realizadas en el pasado, como {motivo_tarea_similar}, considero razonable asignar una estimacion de {estimacion} puntos a la tarea actual."

            motivoPersona1 = f"Basandome en tareas realizadas anteriormente, como {motivo_tarea_similar}, {historico_ejecutor}, podria resolver perfectamente la nueva tarea."
            motivoPersona2 = f"Considerando el historial de tareas previas, como {motivo_tarea_similar}, {historico_ejecutor} demostro habilidades sobresalientes y podrian resolver perfectamente la nueva tarea."
            motivoPersona3 = f"Tomando como referencia trabajos similares previamente completados, {motivo_tarea_similar}, {historico_ejecutor} ha demostrado competencia y podrian abordar con exito la nueva tarea."
            motivoPersona4 = f"Basandome en el desempeño en tareas anteriores, como {motivo_tarea_similar}, {historico_ejecutor} se destaco por su eficiencia y podrian resolver perfectamente la nueva tarea."
            motivoPersona5 = f"Al analizar tareas similares realizadas en el pasado, como {motivo_tarea_similar}, {historico_ejecutor} ha demostrado habilidades excepcionales y podrian abordar la nueva tarea con exito."
                
        lista_motivosEstimacion = [motivoEstimacion1, motivoEstimacion2, motivoEstimacion3, motivoEstimacion4, motivoEstimacion5]
        lista_motivosPersona = [motivoPersona1, motivoPersona2, motivoPersona3, motivoPersona4, motivoPersona5]
        motivoEstimacion =  random.choice(lista_motivosEstimacion)
        motivoPersona =  random.choice(lista_motivosPersona)

    
def darMotivo(tracker)-> bool:
    tarea_asignada = asignarTarea(tracker)
    if tarea_asignada == 0: #Recibio una nueva tarea, por lo que genera un nuevo motivo.
        print("ES 0")
        AsignarJsonDatos()
        generarMotivos(tracker)
        return True
    elif tarea_asignada == 1: #No recibio una nueva tarea, pero tiene una tarea en el slot, por lo que mantiene el motivo de la tarea enviada anteriormente
        print("ES 1")
        return True
    else: #No recibio ninguna tarea.
        print("ES -1")
        return False

class ActionDarMotimoEstimacion(Action):

    def name(self) -> Text:
        return "dar_motivo_estimacion"
        
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global motivoEstimacion
        message = ""
        if darMotivo(tracker) and (motivoEstimacion != ""):
            message = motivoEstimacion
        else:
            message = "Debe indicarme la tarea a la cual desea estimar."
        dispatcher.utter_message(text=message)
        return [SlotSet("tarea",str(tarea))]
    
class ActionDarMotimoPersona(Action):

    def name(self) -> Text:
        return "dar_motivo_persona"
        
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global motivoPersona
        message = ""
        if darMotivo(tracker) and (motivoPersona != ""):
            message = motivoPersona
        else:
            message = "Debe indicarme la tarea a la cual desea asignar a una persona."
        dispatcher.utter_message(text=message)
        return [SlotSet("tarea",str(tarea))]





# Viessmann2HASS
PyScript permettant d'interfacer Home Assistant avec une chaudière Viessmann via un câble Optolink 

La constante PORT est à adapter avec le nom du port série sur lequel est raccordé le câble Optolink.

La constante DOMAIN est à adapter avec le nom de domaine que vous souhaitez pour vos entités.

Le tableau readCmds est à modifier avec les informations que vous souhaiter récupérer de votre chaudière :
  - addr : adresse mémoire à lire 
  - size : taille méroire à lire
  - conv : Données de conversion
  - unit : unité
  - name :'Friendly name'
  - entity : ID de l'entité

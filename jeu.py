import arcade
import cv2
# on va importer mysql-connector-python
import mysql.connector

# on importe datetime pour avoir la date et l'heure
import datetime

import tkinter as tk
from win32api import GetSystemMetrics
import pyscreenrec
import webbrowser
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build


# pour enregistre l'ecran pendant le jeu


# Parametre de la fenetre
largeurFenetre = GetSystemMetrics(0)
hauteurFenetre = GetSystemMetrics(1)
titreFenetre = "Jeu-Platforme"

# modele d'entrainement
teteCascade = cv2.CascadeClassifier('haarcascade_frontalface_alt2.xml')
# on peut etre plus précis en utilisant le modele suivant "haarcascade_frontalface_alt2.xml"

# capture la webcam
captureVideo = cv2.VideoCapture(0)

recorder = pyscreenrec.ScreenRecorder()


# couleur des lignes dans la webcam
couleur = (255, 0, 0)

# Taille de nos sprites
tailleTuile = 1

# parametres du personnage
graviter = 0.3
vitesseDeplacement = 3
vitesseAnimation = 15

# Permet de savoir si le personnage est sur le coté droit ou gauche
faceDroite = 0
faceGauche = 1


# Le nombre de pixels à conserver comme marge minimale entre le personnage et le bord de l'écran.
margeFenetreDroite = 250
margeFenetreBas = 0
margeFenetreHaut = 100


def upload_video(video_filename, pseudo, score):
    # Définissez les jetons d'accès ici
    oauth2 = {
        "access_token": "**",
        "refresh_token": "**",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "**",
        "client_secret": "**"
    }

    # Créez un objet Credentials à partir de vos jetons d'accès
    credentials = Credentials.from_authorized_user_info(info=oauth2)

    # Créez une chaîne de découverte de service YouTube
    youtube = build('youtube', 'v3', credentials=credentials)

    # Définissez les propriétés de la vidéo que vous souhaitez uploader
    video_title = f'{pseudo} a fait un score de {score}'
    video_description = 'This is my video'
    video_tags = ['tag1', 'tag2']

    # Chargez le fichier vidéo que vous souhaitez uploader
    media = MediaFileUpload(video_filename,
                            mimetype='video/mp4',
                            chunksize=1024*1024,
                            resumable=True)

    # Créez une requête de création de vidéo
    request = youtube.videos().insert(
        part="snippet,status",
        body=dict(
            snippet=dict(
                title=video_title,
                description=video_description,
                tags=video_tags
            ),
            status=dict(
                privacyStatus="private"
            )
        ),
        media_body=media
    )

    # Envoyez la requête de création de vidéo
    response = request.execute()

    # Affichez l'ID de la vidéo que vous venez d'uploader
    print(f'Video uploaded with ID: {response["id"]}.')
    return response['id']


# Chargement des textures


def chargerTexture(filename):
    return [

        # Partie droite
        arcade.load_texture(filename),
        # Partie Gauche
        arcade.load_texture(filename, flipped_horizontally=True)
    ]


class Personnage(arcade.Sprite):
    def __init__(self):
        super().__init__()
        # Mettre par default la face droite du personnage
        self.personnageFaceDirection = faceDroite

        # va permetre de basculer entre les differentes images
        self.textureActuelle = 0

        # Hitbox du perssonage
        self.points = [[-10, -10], [10, -10], [10, 22], [-10, 22]]

        # Chargement des textures

        # Sprites
        sprites = "sprites/"

        # Chargement des textures pour se déplacer
        self.textureMarche = []
        for i in range(5):
            texture = chargerTexture(f"{sprites}r{i+1}.png")
            self.textureMarche.append(texture)

        self.total_time = 0.0

    def update_animation(self, delta_time: float = 1/34):
        # permet de savoir si on doit etre sur la face gauche ou celle de droite
        if self.change_x < 0 and self.personnageFaceDirection == faceDroite:
            self.personnageFaceDirection = faceGauche
        elif self.change_x > 0 and self.personnageFaceDirection == faceGauche:
            self.personnageFaceDirection = faceDroite

        # animation du deplacement
        self.textureActuelle += 1
        if self.textureActuelle > 4 * vitesseAnimation:
            self.textureActuelle = 0
        frame = self.textureActuelle // vitesseAnimation
        direction = self.personnageFaceDirection
        self.texture = self.textureMarche[frame][direction]


def popup():
    # on fabrique une belle fenêtre pour demander le nom du joueur
    window = tk.Tk()
    window.title("Nom du joueur")
    window.geometry("500x700")
    window.resizable(True, True)

    # on charge l'image en mémoire
    image = tk.PhotoImage(file="mario.gif")

    # on crée un label pour contenir l'image
    label = tk.Label(window, image=image)
    label.pack()

    # on crée un frame pour contenir le titre
    frame_titre = tk.Frame(window, bg="#7793B2", bd=2, relief=tk.SUNKEN)
    frame_titre.pack(fill=tk.X)

    # on crée un label pour afficher le titre
    label = tk.Label(frame_titre, text="Nom du joueur", font=(
        "Arial", 20, "bold"), fg="white", bg="#7793B2")
    label.pack()

    # on crée un frame pour contenir l'entrée du nom
    frame_nom = tk.Frame(window, bg="#7793B2", bd=2, relief=tk.SUNKEN)
    frame_nom.pack(fill=tk.X)

    # on crée une entrée pour le nom du joueur
    entry = tk.Entry(frame_nom, font=("Arial", 20))
    entry.pack()

    # au clic sur le bouton on récupère le nom
    def getNom():
        global nomJoueur
        nomJoueur = entry.get()
        window.destroy()

    # on crée un frame pour contenir le bouton
    frame_bouton = tk.Frame(window, bg="#7793B2", bd=2, relief=tk.SUNKEN)
    frame_bouton.pack(fill=tk.X)

    # on crée un bouton pour valider le nom du joueur
    button = tk.Button(frame_bouton, text="Valider", font=("Arial", 20), command=getNom,
                       bd=0, relief=tk.SUNKEN, activebackground="#7793B2", activeforeground="white")
    button.pack()

    window.mainloop()


class JeuView(arcade.View):
    # Le jeu

    def setup(self):
        # on lance le record de l'ecran et met le nom du fichier en fonction de la date et de l'heure
        recorder.start_recording(
            f"recording-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.mp4", 10)
        nomvideo = f"recording-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.mp4"
        # on met le nom de la video dans un fichier texte
        with open("nomvideo.txt", "w") as f:
            f.write(nomvideo)
        # Permet de suivre le defillement de la cam
        self.vueBas = 0
        self.vueGauche = 0
        self.total_time = 0.0

        self.nomJoueur = nomJoueur

        # Créer les sprites list
        self.listePersonnage = arcade.SpriteList()

        self.personnage = Personnage()
        self.listeMurs = arcade.SpriteList()
        self.listePieges = arcade.SpriteList()
        self.listeCoffres = arcade.SpriteList()

        self.tailleBackground = 1
        self.calquesBackground = ["self.bc0"]

        for i in range(self.tailleBackground):
            self.calquesBackground[i] = arcade.SpriteList()

        self.personnage.center_x = 80
        self.personnage.center_y = 40

        self.listePersonnage.append(self.personnage)
        ### Chargement de la map sur tiled ###

        # Nom de la map tiled a charger
        nomMap = "mapcoffre3calque.tmx"
        # Noms des calques de la map faite sur tiled que l'on va récuperer
        calqueMur = "Platforms"
        calquePieges = "Piques"
        calqueCoffres = "Coffre"

        # lire la map tiled
        mapTiled = arcade.tilemap.read_tmx(nomMap)

        # on set les murs, les murs vont représenté tout les blocs physique que l'on ne peu traversser
        self.listeMurs = arcade.tilemap.process_layer(
            map_object=mapTiled, layer_name=calqueMur, scaling=tailleTuile, use_spatial_hash=True)

        # on set la liste des pieges
        self.listePieges = arcade.tilemap.process_layer(
            mapTiled, calquePieges, tailleTuile)

        # on set la liste des coffres
        self.listeCoffres = arcade.tilemap.process_layer(
            mapTiled, calqueCoffres, tailleTuile)

        for i in range(self.tailleBackground):
            self.calquesBackground[i] = arcade.tilemap.process_layer(
                mapTiled, str(i), tailleTuile)

        # intialiser le background color
        if mapTiled.background_color:
            arcade.set_background_color(mapTiled.background_color)

        # Créer le moteur phisyque qui va gérer les collision
        self.moteurPhysique = arcade.PhysicsEnginePlatformer(
            self.personnage, self.listeMurs, graviter)

    # si on clique sur échap on revient au menu
    def on_key_release(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            recorder.stop_recording()
            menu_view = MenuView()
            menu_view.setup()
            self.window.show_view(menu_view)

    def on_draw(self):
        # Clear the screen to the background color
        arcade.start_render()

        # Afficher les textures background
        for i in range(self.tailleBackground):
            self.calquesBackground[i].draw()

        # Afficher nos sprites
        self.listeMurs.draw()
        self.listePieges.draw()
        self.listeCoffres.draw()
        self.listePersonnage.draw()

        # on dessine le chrono
        minutes = int(self.total_time) // 60
        seconds = int(self.total_time) % 60
        output = f"Temps: {minutes:02d}:{seconds:02d}"
        # on affiche le chrono le chrono en haut a gauche de l'écran et il va suivre la cam
        arcade.draw_text(output, self.vueGauche + 10, self.vueBas + hauteurFenetre - 50,
                         arcade.color.WHITE, 35)

    def on_update(self, delta_time):

        ### Partie Opencv ###
        _, image = captureVideo.read()

        # mettre l'image en gris
        gris = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # détecter les têtes
        faces = teteCascade.detectMultiScale(gris, 1.1, 4)

        # Dessiner un carer autour de chaque tête
        for (x, y, w, h) in faces:
            ### Deplacement de personnage ###
            # Partie jump droite
            if (x < 325 and y < 250):
                self.personnage.change_x = vitesseDeplacement
                if self.moteurPhysique.can_jump():
                    self.personnage.change_y = 7

            # Partie jump gauche
            if (x > 325 and y < 250):
                self.personnage.change_x = -vitesseDeplacement
                if self.moteurPhysique.can_jump():
                    self.personnage.change_y = 7

            # Partie a gauche
            if (x > 325 and y > 250):
                self.personnage.change_x = -vitesseDeplacement

            # Partie a Droite
            if (x < 325 and y > 250):
                self.personnage.change_x = vitesseDeplacement
            # dessin du carer
            cv2.rectangle(image, (x, y), (x+w, y+h), couleur, 2)

        # on renversse l'image
        image = cv2.flip(image, 1)

        # dessin du background
        cv2.line(image, (325, 500), (325, 0), couleur, 5)
        cv2.line(image, (750, 250), (0, 250), couleur, 5)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(image, 'Gauche', (10, 400), font,
                    2, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, 'Jump Gauche', (30, 100), font,
                    1, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, 'Droite', (355, 400), font,
                    2, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(image, 'Jump Droite', (355, 100), font,
                    1, (255, 255, 255), 2, cv2.LINE_AA)

        # afficher l'image
        cv2.imshow('image', image)

        # Deplacer le personnage avec le moteur physique
        self.moteurPhysique.update()

        # Tcheck si on touche un piege sinon on relance direct la Partie
        if arcade.check_for_collision_with_list(self.personnage, self.listePieges):
            self.personnage.center_x = 100
            self.personnage.center_y = 100
            arcade.set_viewport(self.vueGauche, largeurFenetre +
                                self.vueGauche, self.vueBas, hauteurFenetre + self.vueBas)

        # Si le joueur tombe il respawn sans reset le chrono
        if self.personnage.bottom < -300:

            self.personnage.center_x = 100
            self.personnage.center_y = 100
            arcade.set_viewport(self.vueGauche, largeurFenetre +
                                self.vueGauche, self.vueBas, hauteurFenetre + self.vueBas)

        # Tcheck si on touche le coffre pour afficher la victoire
        if arcade.check_for_collision_with_list(self.personnage, self.listeCoffres):
            # on affiche la victoire
            # on enregistre le temps dans un txt
            with open("score.txt", "a") as f:
                f.write(str(self.total_time) + "\n")

            # on crée une fenetre une popup avec tkinter pour récuperer le nom du joueur

            # on se connecte a la base de donnée mysql et pour ne pas avoir l'erreur Character set 'utf8' unsupported on doit mettre utf8mb4 (mydb.set_charset_collation('utf8mb4', 'utf8mb4_unicode_ci'))

            # on arette de record la video
            recorder.stop_recording()
            # on récupére le dernier nom de video dans le fichier nomVideo.txt
            with open("nomVideo.txt", "r") as f:
                nomVideo = f.read()
                upload_video(nomVideo, self.nomJoueur, str(self.total_time))

            # on affiche la victoire en envoyant le temps au constructeur
            view = VictoireView(self.total_time)
            # on change de vue
            self.window.show_view(view)

        # déplacer le joueur
        self.listePersonnage.update()

        # update les animations du personnage
        self.listePersonnage.update_animation()

        ###Gestion de la camera ###
        # Vérifier si on doit changer la camera

        change = False

        # defilement de la cam vers la gauche si le personnage est a gauche de la cam
        if self.personnage.left > 100:
            limiteGauche = self.vueGauche + 250
        else:
            limiteGauche = self.vueGauche + 0

        if self.personnage.left < limiteGauche:
            if self.personnage.left > 250:
                self.vueGauche -= limiteGauche - self.personnage.left
                change = True

        # defilement de la cam vers la droite si le personnage est a droite de la cam
        right_boundary = self.vueGauche + largeurFenetre - largeurFenetre // 2
        if self.personnage.right > right_boundary:
            self.vueGauche += self.personnage.right - right_boundary
            change = True

        if change:
            # faire défiler que les entiers sinon on se retrouve avec des pixels qui ne sont pas alignés à l'écran.
            self.vueBas = int(self.vueBas)
            self.vueGauche = int(self.vueGauche)

            # Faire le défilement
            arcade.set_viewport(self.vueGauche, largeurFenetre +
                                self.vueGauche, self.vueBas, hauteurFenetre + self.vueBas)
        self.total_time += delta_time

# pour décharger les textures pour éviter les erreurs de mémoire on va créer une fonction

# on va créer une classe pour la vue du menu avec trois boutons


class MenuView(arcade.View):
    def setup(self):

        # on charge les images
        self.background = arcade.load_texture("images/background.jpg")
        self.play = arcade.load_texture("images/Play.png")
        self.score = arcade.load_texture("images/score.png")
        self.quit = arcade.load_texture("images/quit.png")

    def on_draw(self):
        arcade.start_render()
        # on affiche les images en utilisant largeurFenetre et hauteurFenetre pour que l'image face 50% de la fenetre en largeur et 20% en hauteur tout en étant centré et en laissant 10% de marge entre chaque bouton
        # le background prend la taille de la fenetre
        arcade.draw_texture_rectangle(largeurFenetre // 2, hauteurFenetre // 2,
                                      largeurFenetre, hauteurFenetre, self.background)

        arcade.draw_texture_rectangle(largeurFenetre // 2, hauteurFenetre // 2 + hauteurFenetre //
                                      5 + hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5, self.play)
        # pour que l'image ne soit pas étirée, notre image doit faire la même taille que la fenetre donc en largeur
        arcade.draw_texture_rectangle(
            largeurFenetre // 2, hauteurFenetre // 2, largeurFenetre // 2, hauteurFenetre // 5, self.score)
        arcade.draw_texture_rectangle(largeurFenetre // 2, hauteurFenetre // 2 - hauteurFenetre //
                                      5 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5, self.quit)

    def on_mouse_press(self, x, y, button, modifiers):
        # on récupère les positions des images pour les transformer en boutons cliquables
        play = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre // 2 + hauteurFenetre //
                5 + hauteurFenetre // 10 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)
        score = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre //
                 2 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)
        quit = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre // 2 - hauteurFenetre //
                5 - hauteurFenetre // 10 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)

        # on vérifie si on a cliqué sur un bouton
        if x > play[0] and x < play[0] + play[2] and y > play[1] and y < play[1] + play[3]:
            # on change de vue et on insere le nom du joueur dans le constructeur
            game_view = JeuView()
            game_view.setup()
            self.window.show_view(game_view)
        elif x > score[0] and x < score[0] + score[2] and y > score[1] and y < score[1] + score[3]:
            # on change de vue
            score_view = ScoreView()
            score_view.setup()
            self.window.show_view(score_view)
        elif x > quit[0] and x < quit[0] + quit[2] and y > quit[1] and y < quit[1] + quit[3]:
            # on quitte le jeu
            arcade.close_window()

    # quand la souris est au dessus d'un bouton on change l'image pour créer un effet de survol
    def on_mouse_motion(self, x, y, dx, dy):
        play = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre // 2 + hauteurFenetre //
                5 + hauteurFenetre // 10 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)
        score = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre //
                 2 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)
        quit = (largeurFenetre // 2 - largeurFenetre // 4, hauteurFenetre // 2 - hauteurFenetre //
                5 - hauteurFenetre // 10 - hauteurFenetre // 10, largeurFenetre // 2, hauteurFenetre // 5)
        if x > play[0] and x < play[0] + play[2] and y > play[1] and y < play[1] + play[3]:
            self.play = arcade.load_texture("images/play2.png")
        elif x > score[0] and x < score[0] + score[2] and y > score[1] and y < score[1] + score[3]:
            self.score = arcade.load_texture("images/score2.png")
        elif x > quit[0] and x < quit[0] + quit[2] and y > quit[1] and y < quit[1] + quit[3]:
            self.quit = arcade.load_texture("images/quit2.png")
        else:
            self.play = arcade.load_texture("images/Play.png")
            self.score = arcade.load_texture("images/score.png")
            self.quit = arcade.load_texture("images/quit.png")


class VictoireView(arcade.View):
    # la "view" Victoire
    def __init__(self, temps):
        # lance le code des qu'on arrive cette view
        super().__init__()
        self.total_time = temps
        # on charge l'image "victoire.jpg" de victoire au milieu de l'écran
        self.texture = arcade.load_texture("victoire.jpg")
        # on reset la position de la camera arcade pour que le personnage soit au milieu de l'écran et que l'image de victoire soit au milieu de l'écran
        arcade.set_viewport(0, largeurFenetre - 1, 0, hauteurFenetre - 1)

        # on crée une variable pour le nom du joueur
        self.nomJoueur = nomJoueur

        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="test",
            charset='utf8'
        )

        # on crée un curseur pour executer des requetes sql
        mycursor = mydb.cursor()

        # on défini le nom du joueur a "test"

        # on défini la date a la date du jour
        date = datetime.datetime.now()
        # si datetime is not defined il faut faire un import datetime

        # on défini la requete sql
        sql = "INSERT INTO score (joueur,score, date) VALUES (%s, %s, %s)"

        # on défini les valeurs de la requete sql
        val = (self.nomJoueur, self.total_time, date)

        # on execute la requete sql
        mycursor.execute(sql, val)

        # on commit les changements
        mydb.commit()
        # on affiche le chrono récupéré dans le fichier "score.txt", on va récupérer la dernière ligne du fichier

    def on_draw(self):
        # afficher la view
        arcade.start_render()
        self.texture.draw_sized(
            largeurFenetre // 2, hauteurFenetre // 2, largeurFenetre, hauteurFenetre)

        # on affiche le chrono récupéré dans le fichier "score.txt", on va récupérer la dernière ligne du fichier
        with open("score.txt", "r") as fichier:
            lignes = fichier.readlines()
            derniereLigne = lignes[-1]
            # on place le score en haut au milieu de l'écran
            arcade.draw_text(derniereLigne, largeurFenetre // 2, hauteurFenetre - 200,
                             arcade.color.WHITE, font_size=50, anchor_x="center")
            arcade.draw_text("Nom du joueur : " + self.nomJoueur, largeurFenetre // 2, hauteurFenetre - 300,
                             arcade.color.WHITE, font_size=50, anchor_x="center")
    # relancer la partie qu'on on clique sur "R"

    def on_key_press(self, key, modifiers):
        if key == arcade.key.R:
            game_view = JeuView()
            game_view.setup()
            self.window.show_view(game_view)

    # si on clique sur échap on revient au menu
    def on_key_release(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            menu_view = MenuView()
            menu_view.setup()
            self.window.show_view(menu_view)


class ScoreView(arcade.View):

    def setup(self):
        self.texture = arcade.load_texture("images/background.jpg")
        # on fait charger la texture de l'image de fleche pour revenir au menu
        self.fleche = arcade.load_texture("images/fleche.png")
        # on reset la position de la camera arcade pour que le personnage soit au milieu de l'écran et que l'image de score soit au milieu de l'écran
        arcade.set_viewport(0, largeurFenetre - 1, 0, hauteurFenetre - 1)

        mydb = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="test",
            charset='utf8'
        )

        # on crée un curseur pour executer des requetes sql
        mycursor = mydb.cursor()

        # on défini la requete sql et on récupère les 10 meilleurs scores
        sql = "SELECT joueur, score, date FROM score ORDER BY score ASC LIMIT 10"

        # on execute la requete sql
        mycursor.execute(sql)

        # on récupère les résultats de la requete sql que la va récupérer dans draw
        self.resultat = mycursor.fetchall()

    def on_draw(self):
        # on on réutilise le background de la view "menu"
        arcade.start_render()
        # on affiche le background
        self.texture.draw_sized(
            largeurFenetre // 2, hauteurFenetre // 2, largeurFenetre, hauteurFenetre)
        # on affiche la texture de la fleche en haut a gauche de l'écran pour revenir au menu
        self.fleche.draw_sized(50, hauteurFenetre - 50, 100, 100)

        # on créer une grille de 10 lignes et 3 colonnes

        # on affiche le nom des colonnes au centre en allignant le test vers la gauche
        arcade.draw_text("Nom", 500, hauteurFenetre - 100,
                         arcade.color.WHITE, font_size=50, anchor_x="left")
        arcade.draw_text("Score", largeurFenetre // 2 + 50, hauteurFenetre - 100,
                         arcade.color.WHITE, font_size=50, anchor_x="left")
        arcade.draw_text("Date", largeurFenetre - 250, hauteurFenetre - 100,
                         arcade.color.WHITE, font_size=50, anchor_x="right")

        # on parcours les 10 meilleurs scores
        for i in range(10):
            # on affiche le nom du joueur
            arcade.draw_text(self.resultat[i][0], 500, hauteurFenetre - 200 - i * 100,
                             arcade.color.WHITE, font_size=50, anchor_x="left")
            # on affiche le score du joueur
            arcade.draw_text(str(self.resultat[i][1]), largeurFenetre // 2 + 50, hauteurFenetre - 200 - i * 100,
                             arcade.color.WHITE, font_size=50, anchor_x="left")
            # on affiche la date du joueur
            arcade.draw_text(str(self.resultat[i][2]), largeurFenetre - 250, hauteurFenetre - 200 - i * 100,
                             arcade.color.WHITE, font_size=50, anchor_x="right")

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            # on coupe la video

            game_view = MenuView()
            game_view.setup()
            self.window.show_view(game_view)

    def on_mouse_press(self, x, y, button, modifiers):
        # si on clique sur la fleche on revient au menu
        if x > 0 and x < 100 and y > hauteurFenetre - 100 and y < hauteurFenetre:
            game_view = MenuView()
            game_view.setup()
            self.window.show_view(game_view)

        # si on clique sur un score on ouvre une page web
        for i in range(len(self.resultat)):
            if x > largeurFenetre // 2 - 500 and x < largeurFenetre // 2 + 500 and y > hauteurFenetre - 200 - i * 50 - 25 and y < hauteurFenetre - 200 - i * 50 + 25:
                webbrowser.open("https://www.google.com")

    def on_mouse_motion(self, x, y, dx, dy):
        # si on passe la souris sur la fleche on change la couleur de la fleche
        if x > 0 and x < 100 and y > hauteurFenetre - 100 and y < hauteurFenetre:
            self.fleche = arcade.load_texture("images/fleche2.png")
        else:
            self.fleche = arcade.load_texture("images/fleche.png")


def main():
    # on demande le nom du joueur
    popup()

    # on rajoute antialiasing=False pour éviter les problèmes de pixelisation
    window = arcade.Window(largeurFenetre, hauteurFenetre,
                           titreFenetre, antialiasing=False)
    # on récupère le nom du joueur

    # on met le nom du joueur dans une variable accessible dans toutes les classes
    startView = MenuView()
    window.show_view(startView)
    startView.setup()
    # on set le background du jeu en #7793B2 ou rgb(119, 147, 178)
    arcade.set_background_color(arcade.color.SHADOW_BLUE)
    arcade.run()


main()

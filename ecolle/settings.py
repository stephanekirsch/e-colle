# -*- coding:utf8 -*-
# Django settings for e-colle project.

from os import path

# =============================================================================
#                            INFORMATIONS À REMPLIR
# =============================================================================

# le mot de passe à la création de l'admin
DEFAULT_ADMIN_PASSWD = 'admin'

# le mot de passe à la création du compte secrétariat
DEFAULT_SECRETARIAT_PASSWD = 'secret'

# l'email de l'admin. Si vous ne voulez pas en mettre, laissez vide
EMAIL_ADMIN = ''

# l'email du secrétariat. Si vous ne voulez pas en mettre, laissez vide
EMAIL_SECRETARIAT = ''

# True si on veut restreindre la partie admin à certaines adresse IP
# (typiquement des adresse locales), False sinon
IP_FILTRE_ADMIN = True

# liste des adresses autorisées pour la partie admin si IP_FILTRE_ADMIN == True
# à renseigner avec des REGEXP.
IP_FILTRE_ADRESSES = ('^127\.0\.0\.1$')

# True pour faire des jpeg miniatures des pdf de colle. False sinon.
IMAGEMAGICK = True

# les couples nom/email du (des) administrateur(s) du site
ADMINS = (
    ('admin', 'admin@example.com'),
)


# les nom de domaine autorisés pour accéder à e-colle
# démarrer par un '.' pour les sous-domaines (par exemple '.e-colle.fr')
ALLOWED_HOSTS = []

INTERNAL_IPS= ['127.0.0.1']

# une clé secrète de 50 caractères. À modifier à la configuration
SECRET_KEY = 'cg(ip)m3z77z3v!5wo&cl8^4!rk9t0++5wld+@i(kifb!z-k0p'

# fuseau horaire, à changer le cas échéant
TIME_ZONE = 'Europe/Paris'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # le SGBD choisi
        'NAME': 'e-colle',  # le nom de la base de données
        # La suite est à laisser vide si vous utilisez SQlite
        'USER': 'e-colle',  # le nom de l'utilisateur ayant droits
        # sur la base de données.
        'PASSWORD': '',  # le mot de passe de l'utilisateur
        'HOST': 'localhost',  # l'adresse IP de la base de données.
        'PORT': '',  # vide par défaut. À renseigner si la BDD se trouve
        # sur un port particulier.
    }
}

# Style CSS par défaut.
DEFAULT_CSS = "style_css"

# Horaires des colles
# On écrit les heures en minutes depuis minuit.
HEURE_DEBUT = 8*60
HEURE_FIN = 20*60
# L'intervalle entre deux créneaux, en minutes.
INTERVALLE = 30


# =============================================================================
#                        FIN INFORMATIONS À REMPLIR
# =============================================================================

DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000

CHEMINVERSECOLLE = path.dirname(path.dirname(__file__))

# on récupère le nom du SGBD: mysql ou sqlite3 ou postgresql ou oracle.
BDD = DATABASES['default']['ENGINE'].split(".")[-1]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            path.join(CHEMINVERSECOLLE, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


MEDIA_ROOT = path.join(CHEMINVERSECOLLE, 'media')

RESOURCES_ROOT = path.join(CHEMINVERSECOLLE, 'resources')

STATICFILES_DIRS = (
    path.join(CHEMINVERSECOLLE, 'public'),
)


MEDIA_URL = '/media/'

STATIC_URL = '/static/'

DEBUG = False

APPEND_SLASH = False

MANAGERS = ADMINS

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accueil.apps.accueilConfig',
    'administrateur.apps.administrateurConfig',
    'eleve.apps.eleveConfig',
    'colleur.apps.colleurConfig',
    'secretariat.apps.secretariatConfig',
    'app_mobile.apps.appMobileConfig',
    'customfilter.apps.customfilterConfig',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

)

ROOT_URLCONF = 'ecolle.urls'

WSGI_APPLICATION = 'ecolle.wsgi.application'

LANGUAGE_CODE = 'fr_FR'

USE_I18N = True

USE_TZ = False

AUTH_USER_MODEL = "accueil.User"

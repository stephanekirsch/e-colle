# -*- coding:utf8 -*-
# Django settings for e-colle project.

from os import path

from .debug import *

# =============================================================================
#                            INFORMATIONS À REMPLIR
# =============================================================================

from .config import *

# =============================================================================
#                        FIN INFORMATIONS À REMPLIR
# =============================================================================

# les couples nom/email du (des) administrateur(s) du site
ADMINS = (
    ('admin', 'admin@example.com'),
)

DEFAULT_CSS = "style.css"

DATABASES = {
    'default': {
        'ENGINE': "django.db.backends.{}".format(DB_ENGINE),  # le SGBD choisi
        'NAME': DB_NAME,  # le nom de la base de données
        # La suite est à laisser vide si vous utilisez SQlite
        'USER': DB_USER,  # le nom de l'utilisateur ayant droits
        # sur la base de données.
        'PASSWORD': DB_PASSWORD,  # le mot de passe de l'utilisateur
        'HOST': DB_HOST,  # l'adresse IP de la base de données.
        'PORT': DB_PORT,  # vide par défaut. À renseigner si la BDD se trouve
        # sur un port particulier.
    }
}

DATA_UPLOAD_MAX_NUMBER_FIELDS = 100000

FILE_UPLOAD_MAX_MEMORY_SIZE = 6000000

CHEMINVERSECOLLE = path.dirname(path.dirname(__file__))

# on récupère le nom du SGBD: mysql ou sqlite3 ou postgresql ou oracle.
BDD = DB_ENGINE

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
BACKUP_ROOT = path.join(CHEMINVERSECOLLE, 'backup')

RESOURCES_ROOT = path.join(CHEMINVERSECOLLE, 'resources')

STATICFILES_DIRS = (
    path.join(CHEMINVERSECOLLE, 'public'),
)


MEDIA_URL = '/media/'

STATIC_URL = '/static/'

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

LANGUAGE_CODE = 'fr-FR'

USE_I18N = True

USE_TZ = False

AUTH_USER_MODEL = "accueil.User"

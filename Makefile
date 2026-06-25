####################################################
# Ultimate QGIS plugin Makefile
####################################################

# REQUIREMENTS
# 1. This Makefile is for linux environment. It shall be extended to be used on other OS.
# 2. Folder name is the plugin name

# TIPS
# 1. If .ui files are in a subfolder and resources on top level
#     create a file resources_rc.py with:
#     from ..resources_rc import *

####################################################
# CONFIGURATION

# QGIS profile path. Linux default: $HOME/.local/share/QGIS/QGIS3/profiles/default
# macOS default:  $HOME/Library/Application\ Support/QGIS/QGIS3/profiles/default
# Override on the command line:  make deploy QGIS_DIR=/path/to/profile
QGIS_DIR=$(HOME)/.local/share/QGIS/QGIS3/profiles/default
QGIS_BUILD_DIR=

# i18n
LN_DIR=i18n
TRANSLATED_LANG=fr de es

# COMMAND TO RUN DEFAULT APPLICATION (launch a URL)
# Linux 'open' or 'xdg-open' / OSX: 'open' / Win: 'start'
OPEN=xdg-open



###################################################
# DO NOT EDIT BELOW !

PLUGINNAME =$(shell basename $(CURDIR))
VERSION = `cat $(PLUGINNAME)/metadata.txt | grep version | sed 's/version=//'`

PY_FILES = $(filter-out ui_%.py, $(wildcard *.py) $(wildcard **/*.py))
EXTRAS = metadata.txt

UI_SOURCES=$(wildcard *.ui) $(wildcard **/*.ui)
UI_FILES=$(join $(dir $(UI_SOURCES)), $(notdir $(UI_SOURCES:%.ui=%.py)))

LN_SOURCES=$(wildcard *.ts) $(wildcard **/*.ts)
LN_FILES=$(join $(dir $(LN_SOURCES)), $(notdir $(LN_SOURCES:%.ts=%.qm)))

GEN_FILES=${UI_FILES}

all: $(GEN_FILES)

# Use the QGIS-bundled PyQt to compile .ui files. pyuic emits
# `from PyQt5 import ...` literally; rewrite it to `from qgis.PyQt` so the
# generated module works under both PyQt5 (QGIS 3) and PyQt6 (QGIS 4).
$(UI_FILES): %.py: %.ui
	python3 -m qgis.PyQt.uic.pyuic -o $@ $<
	sed -i.bak -E 's/^from PyQt5( import|\.)/from qgis.PyQt\1/' $@ && rm -f $@.bak

$(LN_FILES): %.qm: %.ts
	lrelease $<

clean:
	rm -f $(GEN_FILES) *.pyc
	find $(CURDIR) -iname "*.pyc" -delete

compile: $(UI_FILES) $(LN_FILES)

transup:
	$(foreach lang,$(TRANSLATED_LANG),pylupdate5 -noobsolete $(UI_SOURCES) $(PY_FILES) -ts $(LN_DIR)/$(PLUGINNAME)_$(lang).ts;)

deploy: compile transup
	mkdir -p $(QGIS_DIR)/python/plugins/$(PLUGINNAME)
	cp -rvf * $(QGIS_DIR)/python/plugins/$(PLUGINNAME)/
	rm -f $(QGIS_DIR)/python/plugins/$(PLUGINNAME)/$(PLUGINNAME)*.zip

# The dclean target removes compiled python files from plugin directory
dclean:
	find $(QGIS_DIR)/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete
	rm -f $(QGIS_DIR)/python/plugins/$(PLUGINNAME)/$(PLUGINNAME)*.zip

# The derase deletes deployed plugin
derase:
	rm -Rf $(QGIS_DIR)/python/plugins/$(PLUGINNAME)

zip: clean deploy dclean
	rm -f $(PLUGINNAME)-$(VERSION).zip
	cd $(QGIS_DIR)/python/plugins; zip -9r $(CURDIR)/$(PLUGINNAME)-$(VERSION).zip $(PLUGINNAME)

release: zip
	$(OPEN) http://plugins.qgis.org/plugins/$(PLUGINNAME)/version/add/ &

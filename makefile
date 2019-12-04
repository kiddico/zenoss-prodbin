VERSION      ?= $(shell cat VERSION)
BUILD_NUMBER ?= DEV
BRANCH       ?= develop
ARTIFACT_TAG ?= $(shell echo $(BRANCH) | sed 's/\//-/g')
ARCHIVE      := prodbin.tar.gz
ARTIFACT     := prodbin-$(VERSION)-$(ARTIFACT_TAG).run
TDIR         := build

# Define the name, version and tag name for the docker build image
# Note that build-tools is derived from zenoss-centos-base which contains JSBuilder
BUILD_IMAGE = zenoss-centos-base
BUILD_VERSION = 1.2.26.devtools
BUILD_IMAGE_TAG = zenoss/$(BUILD_IMAGE):$(BUILD_VERSION)

UID := $(shell id -u)
GID := $(shell id -g)

DOCKER = $(shell which docker 2>/dev/null)

DOCKER_RUN := $(DOCKER) run --rm \
		-v $(PWD):/mnt \
		-w /mnt \
		--user $(UID):$(GID) \
		$(BUILD_IMAGE_TAG) \
		/bin/bash -c

.PHONY: all test clean build javascript zensocket build-javascript build-zensocket generate-zversion

default: $(ARTIFACT)
	@echo $< built.

include javascript.mk
include zensocket.mk
include zenoss-version.mk

$(TDIR):
	@mkdir -vp $@

build.dockerfile: build.dockerfile.in
	sed -e "s|%BASE_BUILD_IMAGE%|$(BUILD_IMAGE_TAG)|" -e "s/%GID%/$(GID)/" -e "s/%UID%/$(UID)/" $< > $@
	$(DOCKER) build --tag zenoss/prodbin-build --file ./$@ .

$(ARTIFACT): $(TDIR)/$(ARCHIVE) $(TDIR)/install.sh
	makeself.sh $(TDIR) $@ "Installing zenoss-prodbin component" ./install.sh

ARCHIVE_INCLUSIONS = Products bin etc share legacy/sitecustomize.py setup.py VERSION
ARCHIVE_EXCLUSIONS = --exclude=*.pyc --exclude=*migrate/tests* --exclude=*ZenUITests*
ARCHIVE_TRANSFORMS = --transform="s/legacy\/sitecustomize.py/lib\/python2.7\/sitecustomize.py/"

$(TDIR)/$(ARCHIVE): | $(TDIR)
$(TDIR)/$(ARCHIVE): setup.py $(JSB_TARGETS) $(ZENSOCKET_BINARY) $(VERSION_TARGET) $(VERSION_SCHEMA_TARGET)
	@tar cvzf $@ $(ARCHIVE_EXCLUSIONS) $(ARCHIVE_INCLUSIONS) $(ARCHIVE_TRANSFORMS)

$(TDIR)/install.sh: install.sh | $(TDIR)
	@cp -v $< $@
	@chmod -v +x $@

# equivalent to python setup.py develop
install: setup.py $(JSB_TARGETS) $(ZENSOCKET_BINARY) $(VERSION_TARGET) $(VERSION_SCHEMA_TARGET)
	@python setup.py develop

clean: clean-javascript clean-zensocket clean-zenoss-version
	@rm -vf $(ARTIFACT) build.dockerfile
	@rm -vrf Zenoss.egg-info dist $(TDIR)

# -*- coding: utf-8 -*-

from bobtemplates.plone.base import base_prepare_renderer
from bobtemplates.plone.base import echo
from bobtemplates.plone.base import git_commit
from bobtemplates.plone.base import is_string_in_file
from bobtemplates.plone.base import update_file
from bobtemplates.plone.base import validate_packagename
from lxml import etree
from mrbob.bobexceptions import ValidationError

import os
import re


def pre_theme_name(configurator, question):
    validate_packagename(configurator)

    default = (
        os.path.basename(configurator.target_directory).split(".")[-1].capitalize()
    )
    if default:
        question.default = default


def post_theme_name(configurator, question, answer):
    regex = r"^\w+[a-zA-Z0-9 \.\-_]*\w$"
    if not re.match(regex, answer):
        msg = u"Error: '{0}' is not a valid themename.\n".format(answer)
        msg += u"Please use a valid name (like 'Tango' or 'my-tango.com')!\n"
        msg += u"At beginning or end only letters|diggits are allowed.\n"
        msg += u"Inside the name also '.-_' are allowed.\n"
        msg += u"No umlauts!"
        raise ValidationError(msg)
    return answer


def prepare_renderer(configurator):
    echo("Using theme_barceloneta subtemplate:", "info")
    configurator = base_prepare_renderer(configurator)
    configurator.variables["template_id"] = "theme_barceloneta"

    def normalize_theme_name(value):
        value = "-".join(value.split("_"))
        value = "-".join(value.split())
        return value

    configurator.variables["theme.normalized_name"] = normalize_theme_name(
        configurator.variables.get("theme.name")
    ).lower()

    # configurator.target_directory = configurator.variables['package_folder']


def _update_metadata_xml(configurator):
    """Add plone.app.theming dependency metadata.xml in Generic Setup
    profiles."""
    metadata_file_name = u"metadata.xml"
    metadata_file_dir = u"profiles/default"
    metadata_file_path = (
        configurator.variables["package_folder"]
        + "/"
        + metadata_file_dir
        + "/"
        + metadata_file_name
    )

    with open(metadata_file_path, "r") as xml_file:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(xml_file, parser)
        dependencies = tree.xpath("/metadata/dependencies")[0]
        dep = "profile-plone.app.theming:default"
        dep_exists = False
        for e in dependencies.iter("dependency"):
            dep_name = e.text
            if dep_name == dep:
                dep_exists = True

        if dep_exists:
            print("{dep} already in metadata.xml, skip adding!".format(dep=dep))
            return
        dep_element = etree.Element("dependency")
        dep_element.text = dep
        dependencies.append(dep_element)

    with open(metadata_file_path, "wb") as xml_file:
        tree.write(xml_file, pretty_print=True, xml_declaration=True, encoding="utf-8")


def _update_configure_zcml(configurator):
    file_name = u"configure.zcml"
    file_path = configurator.variables["package_folder"] + "/" + file_name
    namespaces = {"plone": "http://namespaces.plone.org/plone"}

    with open(file_path, "r") as xml_file:
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(xml_file, parser)
        tree_root = tree.getroot()
        theme_name = configurator.variables["theme.normalized_name"]
        theme_xpath = "./plone:static[@name='{0}']".format(theme_name)
        if len(tree_root.xpath(theme_xpath, namespaces=namespaces)):
            print(
                "{name} already in configure.zcml, skip adding!".format(name=theme_name)
            )
            return

    match_str = "-*- extra stuff goes here -*-"
    insert_str = """
  <plone:static
      directory="theme"
      type="theme"
      name="{0}"
      />

""".format(
        configurator.variables["theme.normalized_name"]
    )
    update_file(configurator, file_path, match_str, insert_str)


def _update_setup_py(configurator):
    file_name = u"setup.py"
    file_path = configurator.variables["package.root_folder"] + "/" + file_name
    match_str = "-*- Extra requirements: -*-"
    insert_strings = [
        # "collective.themesitesetup",  # disable while not ready for Plone 5.2
        # "collective.themefragments",  # disable while not ready for Plone 5.2
        # "plone.app.themingplugins",  # disable while not ready for Plone 5.2
    ]
    for insert_str in insert_strings:
        insert_str = "        '{0}',\n".format(insert_str)
        if is_string_in_file(configurator, file_path, insert_str):
            continue
        update_file(configurator, file_path, match_str, insert_str)


def post_renderer(configurator):
    """"""
    _update_configure_zcml(configurator)
    _update_setup_py(configurator)
    _update_metadata_xml(configurator)
    git_commit(
        configurator, "Add theme: {0}".format(configurator.variables["theme.name"])
    )

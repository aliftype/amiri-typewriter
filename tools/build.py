#!/usr/bin/env python2
# encoding: utf-8

from __future__ import division

import argparse
import math
import fontforge
from datetime import datetime
from tempfile import NamedTemporaryFile
from fontTools.ttLib import TTFont

def zeromarks(font):
    """Since this is a fixed width font, we make all glyphs the same width (which allows
    us to set isFixedPitch bit in the post table, that some application rely on
    to identify fixed width fonts). Compliant layout engines will zero the mark
    width when combined, so this is not an issue, but some non-compliant
    engines like Core Text don’t do this and break the font, so we will zero
    the width ourselves here to workaround this."""
    langsystems = set()
    for lookup in font.gpos_lookups:
        for feature in font.getLookupInfo(lookup)[2]:
            for langsys in feature[1]:
                script = langsys[0]
                for language in langsys[1]:
                    langsystems.add((script, language))
    fea = ""
    for script, language in langsystems:
        fea += "languagesystem %s %s;" % (script, language)
    fea += "feature mark {"
    for glyph in font.glyphs():
        if glyph.glyphclass == "mark":
            fea += "pos %s -%d;" % (glyph.glyphname, glyph.width)
    fea += "} mark;"
    with NamedTemporaryFile("w+", suffix=".fea") as tmp:
        tmp.write(fea)
        font.mergeFeature(tmp.name)

def merge(args):
    arabic = fontforge.open(args.arabicfile)
    arabic.encoding = "Unicode"
    arabic.mergeFeature(args.feature_file)

    latin = fontforge.open(args.latinfile)
    latin.encoding = "Unicode"
    scale = arabic["arAlef.isol"].width / latin["space"].width
    latin.em = int(math.ceil(scale * latin.em))

    latin_locl = ""
    for glyph in latin.glyphs():
        if glyph.glyphclass == "mark":
            glyph.width = latin["A"].width
        if glyph.color == 0xff0000:
            latin.removeGlyph(glyph)
        else:
            if glyph.glyphname in arabic:
                name = glyph.glyphname
                glyph.unicode = -1
                glyph.glyphname = name + ".latin"
                if not latin_locl:
                    latin_locl = "feature locl {lookupflag IgnoreMarks; script latn;"
                latin_locl += "sub %s by %s;" % (name, glyph.glyphname)

    with NamedTemporaryFile(suffix=".sfd") as tmp:
        latin.save(tmp.name)
        arabic.mergeFonts(tmp.name)

    if latin_locl:
        latin_locl += "} locl;"
        with NamedTemporaryFile("w+", suffix=".fea") as tmp:
            tmp.write(latin_locl)
            arabic.mergeFeature(tmp.name)

    zeromarks(arabic)

    # Set metadata
    arabic.version = args.version

    copyright = 'Copyright © 2015-%s The Amiri Typewriter Project Authors, with Reserved Font Name "Fira".' % datetime.now().year

    arabic.copyright = copyright.replace("©", "(c)")

    en = "English (US)"
    arabic.appendSFNTName(en, "Copyright", copyright)
    arabic.appendSFNTName(en, "Designer", "Khaled Hosny")
    arabic.appendSFNTName(en, "License URL", "http://scripts.sil.org/OFL")
    arabic.appendSFNTName(en, "License", 'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: http://scripts.sil.org/OFL')
    arabic.appendSFNTName(en, "Descriptor", "Amiri Typewriter is an Arabic monospaced font family inspired by the type of mechanical Arabic typewriters.")
    arabic.appendSFNTName(en, "Sample Text", "الخط هندسة روحانية ظهرت بآلة جسمانية")
    arabic.appendSFNTName(en, "UniqueID", "%s;%s;%s" % (arabic.version, arabic.os2_vendor, arabic.fontname))

    return arabic

def generate(args, font):
    flags = ["round", "opentype"]
    font.generate(args.out_file, flags=flags)

    font = TTFont(args.out_file)

    # Filter-out useless Macintosh names
    name = font["name"]
    name.names = [n for n in name.names if n.platformID != 1]

    # https://github.com/fontforge/fontforge/pull/3235
    head = font["head"]
    # fontDirectionHint is deprecated and must be set to 2
    head.fontDirectionHint = 2
    # unset bits 6..10
    head.flags &= ~0x7e0

    # Drop useless table with timestamp
    if "FFTM" in font:
        del font["FFTM"]

    font.save(args.out_file)

def main():
    parser = argparse.ArgumentParser(description="Create a version of Amiri with colored marks using COLR/CPAL tables.")
    parser.add_argument("arabicfile", metavar="FILE", help="input font to process")
    parser.add_argument("latinfile", metavar="FILE", help="input font to process")
    parser.add_argument("--out-file", metavar="FILE", help="output font to write", required=True)
    parser.add_argument("--feature-file", metavar="FILE", help="output font to write", required=True)
    parser.add_argument("--version", metavar="version", help="version number", required=True)

    args = parser.parse_args()

    font = merge(args)
    generate(args, font)

if __name__ == "__main__":
    main()

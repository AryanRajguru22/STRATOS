"""Build deliverables/viva/STRATOS_Complete_Product_Viva_Handbook.pdf

    python deliverables/viva/build/build_handbook.py

Needs requirements-docs.txt (reportlab, pymupdf) and Pillow. Set STRATOS_TEST_PYTHON to a Python with the application
requirements installed so that per-file test counts can be collected exactly (defaults to the current interpreter).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import facts  # noqa: E402
import handbook_part1 as p1  # noqa: E402
import handbook_part2 as p2  # noqa: E402
from viva_lib import (CALL, Doc, H1, H1X, NextPageTemplate, P, PB, SP, T, cover_painter, glyph_report, make_toc)  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "STRATOS_Complete_Product_Viva_Handbook.pdf")
VERSION = "1.0"


def main():
    F = facts.collect()
    tree = "clean" if F["tree_clean_apart_from_pdfs"] else "NOT clean: " + "; ".join(F["dirty_paths"][:3])
    cover = cover_painter(
        ["Complete Product and", "Technical Viva Handbook"],
        ["Strategic Behavior in University Course / Project Team Formation", "For all four team members: read before the physical viva"],
        [("Document", f"STRATOS Complete Product and Technical Viva Handbook, version {VERSION}"),
         ("Generated", F["date"]),
         ("Built from commit", f"{F['commit']}  (branch {F['branch']}); the PDFs are added in the next commit"),
         ("Tests recorded on", f"{F['tests_commit'][:7]}: {F['tests_passed']} passed, {F['tests_failed']} failed, {F['tests_skipped']} skipped"),
         ("Working tree at build", tree),
         ("Team", "Aryan Rajguru, Harsh Kumar Singh, Ayush, Kashish"),
         ("Status", "Pending verification items are listed in section 0; read them first"),
         ("Data", "All student data and weights are fictional and synthetic")])
    doc = Doc(OUT, "STRATOS Complete Product and Technical Viva Handbook",
              "STRATOS · Complete Product and Technical Viva Handbook · v" + VERSION,
              f"commit {F['short']} · generated {F['date']} · synthetic data", cover)
    story = [NextPageTemplate("body"), PB(), H1X("Contents"), SP(4)]
    toc = make_toc()
    story += [toc, PB()]
    story += [H1("How to use this handbook")]
    story += [P("Read sections 0 to 5 once, front to back: they give you the whole product and the mathematics. Use section 6 together with the running app. "
                "Section 9 is the question bank for rehearsal (cover the answers and speak yours aloud). Section 10 tells you what you may truthfully say about who did what. "
                "The companion document, **STRATOS_Viva_Speaking_Plan_and_Demo.pdf**, tells each person what to say and do on the day.")]
    story += [CALL("note", "Ground rules for the viva",
                   ["1. Say **\"stable against unilateral deviations\"**, never \"optimal\".",
                    "2. Say the data is **synthetic**.",
                    "3. Claim only what you did. For everything else say \"I understand it and can explain it\".",
                    "4. If you do not know, say how you would find out (for example: \"I would check `docs/MODEL.md`\" or \"I would run the engine report\")."])]
    story += p1.section0_status(F)
    story += p1.section1_overview(F)
    story += p1.section2_architecture(F)
    story += p1.section3_model(F)
    story += p1.section4_worked(F)
    story += p1.section5_results(F)
    story += p2.section6_frontend(F)
    story += p2.section7_testing(F)
    story += p2.section8_install(F)
    story += p2.section9_questions(F)
    story += p2.section10_ownership(F)
    doc.build_doc(story)
    missing = glyph_report(OUT)
    print("written:", OUT, os.path.getsize(OUT), "bytes")
    print("missing glyphs:", missing[:20] if missing else "none")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

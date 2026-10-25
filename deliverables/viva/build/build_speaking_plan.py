"""Build deliverables/viva/STRATOS_Viva_Speaking_Plan_and_Demo.pdf  (see build_handbook.py for requirements)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import facts  # noqa: E402
import speaking_plan as sp  # noqa: E402
from viva_lib import (CALL, Doc, H1X, NextPageTemplate, P, PB, SP, cover_painter, glyph_report, make_toc, TEAL)  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "STRATOS_Viva_Speaking_Plan_and_Demo.pdf")
VERSION = "1.0"


def main():
    F = facts.collect()
    D = sp.demo_facts(F)
    tree = "clean" if F["tree_clean_apart_from_pdfs"] else "NOT clean: " + "; ".join(F["dirty_paths"][:3])
    cover = cover_painter(
        ["Four-Member Viva", "Speaking Plan and Demo"],
        ["Strategic Behavior in University Course / Project Team Formation", "Who says what, what to show, and how to answer: Aryan, Harsh, Ayush, Kashish"],
        [("Document", f"STRATOS Viva Speaking Plan and Demonstration Script, version {VERSION}"),
         ("Generated", F["date"]),
         ("Built from commit", f"{F['commit']}  (branch {F['branch']}); the PDFs are added in the next commit"),
         ("Tests recorded on", f"{F['tests_commit'][:7]}: {F['tests_passed']} passed, {F['tests_failed']} failed, {F['tests_skipped']} skipped"),
         ("Demo verified on", f"real Chrome run of the app files of commit c94f918 ({F['n_shots']} states, repo at {F['shots_commit'][:7]})"),
         ("Working tree at build", tree),
         ("Companion", "STRATOS_Complete_Product_Viva_Handbook.pdf"),
         ("Data", "All student data and weights are fictional and synthetic")],
        accent=TEAL)
    doc = Doc(OUT, "STRATOS Viva Speaking Plan and Demonstration Script", "STRATOS · Four-Member Viva Speaking Plan and Demo · v" + VERSION,
              f"commit {F['short']} · generated {F['date']} · synthetic data", cover)
    story = [NextPageTemplate("body"), PB(), H1X("Contents"), SP(4), make_toc(), PB()]
    story += sp.front(F)
    story += sp.order_and_timing(F)
    story += sp.card_kashish(F, D)
    story += sp.card_aryan(F, D)
    story += sp.card_harsh(F, D)
    story += sp.card_ayush(F, D)
    story += sp.runbook(F, D)
    story += sp.handoffs(F, D)
    story += sp.checklist(F, D)
    doc.build_doc(story)
    missing = glyph_report(OUT)
    print("written:", OUT, os.path.getsize(OUT), "bytes")
    print("missing glyphs:", missing[:20] if missing else "none")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())

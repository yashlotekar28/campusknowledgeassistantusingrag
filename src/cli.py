"""Command line tool for ingesting campus documents and testing queries."""

import argparse
import sys
from pathlib import Path
from src.assistant import CampusKnowledgeAssistant


def cmd_ingest(assistant: CampusKnowledgeAssistant, args: argparse.Namespace) -> None:
    target = Path(args.path)
    if target.is_file() and target.suffix.lower() == ".pdf":
        print(f"[*] Ingesting PDF: {target.name}")
        res = assistant.ingest_pdf(target)
        print(f"[+] Ingested {res['chunks_created']} chunks from {res['pages_extracted']} pages.")
    elif target.is_dir():
        pdfs = list(target.glob("**/*.pdf"))
        print(f"[*] Found {len(pdfs)} PDF(s) in {target}...")
        for p in pdfs:
            print(f"  -> Ingesting {p.name}...")
            res = assistant.ingest_pdf(p)
            print(f"     Extracted {res['pages_extracted']} pages, created {res['chunks_created']} chunks.")
    else:
        print(f"[!] Path not found or not a PDF: {target}", file=sys.stderr)


def cmd_query(assistant: CampusKnowledgeAssistant, args: argparse.Namespace) -> None:
    print(f"\n[Q] Question: {args.question}\n")
    res = assistant.ask(args.question, top_k=args.top_k)
    print("=== Answer ===")
    print(res["answer"])
    if res["sources"]:
        print("\n=== Sources ===")
        for s in res["sources"]:
            print(f"- {s['source']}, page {s['page_number']}")
    print(f"\n(Response time: {res['response_time']}s)")


def cmd_stats(assistant: CampusKnowledgeAssistant, args: argparse.Namespace) -> None:
    count = assistant.vector_db.count()
    print(f"[*] Total indexed chunks in database: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Campus Knowledge Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest
    parser_ingest = subparsers.add_parser("ingest", help="Ingest a PDF or folder of PDFs")
    parser_ingest.add_argument("path", help="PDF file or directory of PDFs")

    # Query
    parser_query = subparsers.add_parser("query", help="Ask a question")
    parser_query.add_argument("question", help="Question text")
    parser_query.add_argument("--top-k", type=int, default=3, help="Number of chunks to retrieve")

    # Stats
    parser_stats = subparsers.add_parser("stats", help="Check database statistics")

    args = parser.parse_args()
    assistant = CampusKnowledgeAssistant()

    if args.command == "ingest":
        cmd_ingest(assistant, args)
    elif args.command == "query":
        cmd_query(assistant, args)
    elif args.command == "stats":
        cmd_stats(assistant, args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Migration validation script for Memory & State Management refactoring.

Validates that all new components are properly installed and configured.
Run this after pulling the refactoring changes and installing new dependencies.

Usage:
    python validate_refactoring.py [--init] [--check-chromadb]
    
Options:
    --init              Initialize empty databases (first run)
    --check-chromadb    Download and verify sentence-transformers embedding model
"""

import sys
import sqlite3
import argparse
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def check_python_version():
    """Verify Python 3.8+"""
    if sys.version_info < (3, 8):
        logger.error(f"Python 3.8+ required, got {sys.version}")
        return False
    logger.info(f"✓ Python {sys.version.split()[0]}")
    return True


def check_imports():
    """Verify required packages are installed."""
    packages = [
        ("chromadb", "ChromaDB"),
        ("sentence_transformers", "Sentence Transformers"),
        ("sqlite3", "SQLite3"),
        ("langgraph", "LangGraph"),
    ]
    
    all_ok = True
    for module, name in packages:
        try:
            __import__(module)
            logger.info(f"✓ {name}")
        except ImportError as e:
            logger.error(f"✗ {name}: {e}")
            all_ok = False
    
    return all_ok


def check_file_structure():
    """Verify key files exist."""
    files_to_check = [
        "tradingagents/portfolio_manager.py",
        "tradingagents/agents/utils/memory.py",
        "tradingagents/graph/propagation.py",
        "tradingagents/graph/context_merger.py",
        "tradingagents/agents/managers/risk_engine.py",
        "tradingagents/agents/utils/agent_states.py",
    ]
    
    all_ok = True
    for filepath in files_to_check:
        if Path(filepath).exists():
            logger.info(f"✓ {filepath}")
        else:
            logger.error(f"✗ {filepath} (not found)")
            all_ok = False
    
    return all_ok


def check_database_schema():
    """Verify SQLite portfolio database schema."""
    db_path = Path("./trade_memory/portfolio.db")
    
    if not db_path.parent.exists():
        logger.warning(f"Database directory not created yet: {db_path.parent}")
        logger.info("  Database will be auto-created on first PortfolioManager() call")
        return True
    
    if not db_path.exists():
        logger.warning(f"Database file not created yet: {db_path}")
        logger.info("  Database will be auto-created on first PortfolioManager() call")
        return True
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check portfolio_state table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='portfolio_state'"
        )
        if cursor.fetchone():
            logger.info("✓ portfolio_state table exists")
        else:
            logger.error("✗ portfolio_state table missing")
            return False
        
        # Check trade_history table
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='trade_history'"
        )
        if cursor.fetchone():
            logger.info("✓ trade_history table exists")
        else:
            logger.error("✗ trade_history table missing")
            return False
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"✗ Database check failed: {e}")
        return False


def check_chromadb_collections():
    """Verify ChromaDB collections exist."""
    chroma_path = Path("./trade_memory/chromadb")
    
    if not chroma_path.exists():
        logger.warning(f"ChromaDB directory not created yet: {chroma_path}")
        logger.info("  ChromaDB will be auto-created on first VectorizedMemory() call")
        return True
    
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(chroma_path))
        collections = client.list_collections()
        
        if not collections:
            logger.warning("No ChromaDB collections found yet")
            logger.info("  Collections will be auto-created when agents initialize memories")
            return True
        
        logger.info(f"✓ Found {len(collections)} ChromaDB collections:")
        for coll in collections:
            count = coll.count() if hasattr(coll, 'count') else '?'
            logger.info(f"  - {coll.name}: {count} situations")
        
        return True
    except Exception as e:
        logger.error(f"✗ ChromaDB check failed: {e}")
        return False


def init_databases():
    """Initialize empty databases."""
    logger.info("\n=== Initializing Databases ===")
    
    try:
        from tradingagents.portfolio_manager import PortfolioManager
        logger.info("Creating portfolio database...")
        pm = PortfolioManager(db_path="./trade_memory/portfolio.db")
        portfolio = pm.load_latest_portfolio()
        logger.info(f"✓ Portfolio initialized: ${portfolio['cash_usd']:.2f} cash")
    except Exception as e:
        logger.error(f"✗ Failed to initialize portfolio database: {e}")
        return False
    
    try:
        from tradingagents.agents.utils.memory import VectorizedMemory
        logger.info("Creating ChromaDB collections...")
        
        memory_names = [
            "bull_researcher",
            "bear_researcher",
            "trader",
            "invest_judge",
            "risk_manager",
        ]
        
        for name in memory_names:
            mem = VectorizedMemory(name, db_path="./trade_memory/chromadb")
            logger.info(f"✓ Initialized {name} memory")
    except Exception as e:
        logger.error(f"✗ Failed to initialize ChromaDB: {e}")
        return False
    
    logger.info("\n✓ All databases initialized successfully!")
    return True


def download_embeddings():
    """Download sentence-transformers embedding model."""
    logger.info("\n=== Downloading Embedding Model ===")
    logger.info("This downloads ~100MB model on first use...")
    logger.info("Model: sentence-transformers/all-MiniLM-L6-v2")
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info("Downloading embeddings model...")
        model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2",
            device="cpu"  # Use CPU to avoid CUDA requirement
        )
        
        # Test with a simple sentence
        test_embedding = model.encode("Test embedding")
        logger.info(f"✓ Model downloaded and tested")
        logger.info(f"  Embedding dimension: {len(test_embedding)}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to download embeddings model: {e}")
        logger.info("  You can download manually by running:")
        logger.info("  python -c \"from sentence_transformers import SentenceTransformer; "
                   "SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')\"")
        return False


def main():
    """Run all validation checks."""
    parser = argparse.ArgumentParser(description="Validate refactoring setup")
    parser.add_argument("--init", action="store_true", help="Initialize databases")
    parser.add_argument("--check-chromadb", action="store_true", 
                       help="Download and verify embedding model")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Memory & State Management Refactoring - Validation")
    logger.info("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_imports),
        ("File Structure", check_file_structure),
        ("SQLite Database", check_database_schema),
        ("ChromaDB Collections", check_chromadb_collections),
    ]
    
    results = {}
    for name, check_func in checks:
        logger.info(f"\n=== Checking {name} ===")
        results[name] = check_func()
    
    if args.init:
        results["Database Initialization"] = init_databases()
    
    if args.check_chromadb:
        results["Embedding Model"] = download_embeddings()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✓ All checks passed! System ready for refactored code.")
        return 0
    else:
        logger.error("\n✗ Some checks failed. See above for details.")
        logger.error("\nQuick fixes:")
        logger.error("1. Install missing packages: pip install -r REQUIREMENTS_UPDATE.txt")
        logger.error("2. Initialize databases: python validate_refactoring.py --init")
        logger.error("3. Download embeddings: python validate_refactoring.py --check-chromadb")
        return 1


if __name__ == "__main__":
    sys.exit(main())

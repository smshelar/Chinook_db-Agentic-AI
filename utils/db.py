"""
utils/db.py
-----------
Database connection and schema introspection helper.
Keeps all DB logic in one place so agents stay clean.
"""

import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "chinook.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection to Chinook. Read-only for safety."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema_description() -> str:
    """
    Returns a human-readable schema string for the Chinook DB.
    This is injected into the SQL Writer agent's prompt so it
    knows which tables and columns exist.
    """
    schema = """
Chinook Database Schema (SQLite):

TABLE Artist       : ArtistId (PK), Name
TABLE Album        : AlbumId (PK), Title, ArtistId (FK -> Artist)
TABLE Track        : TrackId (PK), Name, AlbumId (FK), MediaTypeId (FK),
                     GenreId (FK), Composer, Milliseconds, Bytes, UnitPrice
TABLE Genre        : GenreId (PK), Name
TABLE MediaType    : MediaTypeId (PK), Name
TABLE Playlist     : PlaylistId (PK), Name
TABLE PlaylistTrack: PlaylistId (FK), TrackId (FK)
TABLE Employee     : EmployeeId (PK), LastName, FirstName, Title,
                     ReportsTo, BirthDate, HireDate, Address, City,
                     State, Country, PostalCode, Phone, Fax, Email
TABLE Customer     : CustomerId (PK), FirstName, LastName, Company,
                     Address, City, State, Country, PostalCode,
                     Phone, Fax, Email, SupportRepId (FK -> Employee)
TABLE Invoice      : InvoiceId (PK), CustomerId (FK), InvoiceDate,
                     BillingAddress, BillingCity, BillingState,
                     BillingCountry, BillingPostalCode, Total
TABLE InvoiceLine  : InvoiceLineId (PK), InvoiceId (FK), TrackId (FK),
                     UnitPrice, Quantity

Key relationships:
- Invoice.CustomerId -> Customer.CustomerId
- InvoiceLine.InvoiceId -> Invoice.InvoiceId
- InvoiceLine.TrackId -> Track.TrackId
- Track.AlbumId -> Album.AlbumId
- Album.ArtistId -> Artist.ArtistId
- Track.GenreId -> Genre.GenreId
"""
    return schema.strip()


def run_query(sql: str) -> pd.DataFrame:
    """
    Execute a SELECT query and return results as a DataFrame.
    Raises ValueError if the query is not a SELECT (safety guard).
    """
    sql_clean = sql.strip().upper()
    if not sql_clean.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    
    with get_connection() as conn:
        df = pd.read_sql_query(sql, conn)
    return df

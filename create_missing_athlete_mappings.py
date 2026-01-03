"""
Create missing athlete mappings for NULL names in EVENT_STATS_VIEW

Inserts mappings into ATHLETE_SOURCE_IDS for athletes that were matched by name
but have slightly different sail numbers in heat data vs results data.
"""

import mysql.connector

# Read env from .env.production
env_vars = {}
with open('.env.production') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            env_vars[key] = value

def get_connection():
    """Create connection to production database"""
    conn = mysql.connector.connect(
        host='10.0.151.92',
        port=3306,
        database='jfa_heatwave_db',
        user=env_vars['DB_USER'],
        password=env_vars['DB_PASSWORD'],
        connect_timeout=30
    )
    return conn

def main():
    # Mappings to create based on investigation
    # Format: (athlete_id, source_athlete_id, athlete_name, notes)
    mappings = [
        (65, 'Salmonn_G-901', 'Julian Salmonn', 'Sail changed G-21 → G-901'),
        (32, 'Mauch_G-103', 'Moritz Mauch', 'Sail changed GC-103 → G-103'),
        (19, 'Stillrich_G-95', 'Alessio Lucca Stillrich', 'Sail changed E-95 → G-95'),
        (139, 'Stenta_ITA-662', 'Caterina Stenta', 'Sail format I-662 vs ITA-662'),
        (13, 'Katz_SUI-678', 'Pauline Katz', 'Sail changed SUI-4 → SUI-678'),
        (170, 'Benvenuti_I-38', 'Greta Benvenuti', 'Sail format ITA-38 vs I-38'),
        (162, 'Cappuzzo_ITA-333', 'Francesco Cappuzzo', 'Sail format I-333 vs ITA-333'),
        (484, 'Zoia_I-17', 'Serena Zoia', 'Sail changed ESP-17 → I-17'),
        (67, 'Meldrum_K-579', 'Lucas Meldrum', 'Sail changed K-90 → K-579'),
        (172, 'Haggstrom_swe-7', 'Gustav Haggstrom', 'Sail changed S-7 → swe-7'),
        (225, 'Erdil_TUR-33', 'Lena Aylin Erdil', 'Sail changed GER-33 → TUR-33'),
        (6, 'Andres_ESP-2', 'Maria Andres', 'Sail format E-2 vs ESP-2'),
        (504, 'Hölzl_AUT-123', 'Ulrike Hölzl', 'Sail format AT-123 vs AUT-123'),
        (188, 'Tyger_BR-44', 'Jahdan Tyger', 'Sail format BRA-44 vs BR-44'),
        (488, 'Bem_CZE-22', 'Stanislav Bem', 'Sail changed CZE-222 → CZE-22'),
        (510, 'Borlin_S-141', 'Victor Borlin', 'Sail changed E-141 → S-141'),
        (201, 'Mossink_H-226', 'Josanne Mossink', 'Sail changed H-622 → H-226'),
        (528, 'Bail_GER-150', 'Sebastian Bail', 'New sail number GER-150'),
        (490, 'Kolpikova Bala_ESP-0000', 'Svetlana Kolpikova Bala', 'Sail changed ESP-1010 → ESP-0000'),
        (117, 'Zollet_I-115', 'Annamaria Zollet', 'Sail changed I-908 → I-115'),
        # Katz_SUI-14 is a duplicate of Pauline Katz (ID 13)
        (13, 'Katz_SUI-14', 'Pauline Katz', 'Sail changed SUI-4 → SUI-14'),
    ]

    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 100)
    print("CREATING MISSING ATHLETE MAPPINGS")
    print("=" * 100)

    print(f"\n📋 Preparing to insert {len(mappings)} mappings into ATHLETE_SOURCE_IDS")
    print(f"   Source: PWA_heat")
    print("=" * 100)

    # Check which ones already exist
    existing = []
    new = []

    for athlete_id, source_id, name, notes in mappings:
        cursor.execute("""
            SELECT id FROM ATHLETE_SOURCE_IDS
            WHERE source = 'PWA_heat' AND source_id = %s
        """, (source_id,))

        if cursor.fetchone():
            existing.append((athlete_id, source_id, name))
        else:
            new.append((athlete_id, source_id, name, notes))

    if existing:
        print(f"\n⚠️  {len(existing)} mappings already exist (skipping):")
        for athlete_id, source_id, name in existing:
            print(f"   - {source_id} → {name}")

    if new:
        print(f"\n✅ Inserting {len(new)} new mappings:")
        for athlete_id, source_id, name, notes in new:
            print(f"   - {source_id:<35} → {name:<30} ({notes})")

        # Insert new mappings
        insert_sql = """
            INSERT INTO ATHLETE_SOURCE_IDS (athlete_id, source, source_id)
            VALUES (%s, 'PWA_heat', %s)
        """

        for athlete_id, source_id, name, notes in new:
            cursor.execute(insert_sql, (athlete_id, source_id))

        conn.commit()
        print(f"\n✅ Successfully inserted {len(new)} mappings!")

    else:
        print("\n✅ All mappings already exist!")

    # Verify the fix
    print("\n" + "=" * 100)
    print("VERIFICATION: Checking NULL athlete names after mappings")
    print("=" * 100)

    cursor.execute("""
        SELECT COUNT(*) as total_scores,
               SUM(CASE WHEN athlete_name IS NULL THEN 1 ELSE 0 END) as null_names
        FROM EVENT_STATS_VIEW
    """)
    result = cursor.fetchone()
    total = result[0]
    nulls = result[1]

    print(f"\nTotal scores in EVENT_STATS_VIEW: {total}")
    print(f"Scores with NULL athlete_name: {nulls}")

    if nulls == 0:
        print("✅ Perfect! All athlete names are now populated!")
    else:
        pct = (nulls / total * 100) if total > 0 else 0
        print(f"⚠️  Still {nulls} NULL names ({pct:.2f}%)")

        # Show remaining NULLs
        cursor.execute("""
            SELECT DISTINCT athlete_id, source
            FROM EVENT_STATS_VIEW
            WHERE athlete_name IS NULL
            LIMIT 10
        """)
        remaining = cursor.fetchall()
        if remaining:
            print(f"\nRemaining NULLs:")
            for row in remaining:
                print(f"   - {row[1]}: {row[0]}")

    cursor.close()
    conn.close()

    print("\n" + "=" * 100)
    print("✅ MAPPING CREATION COMPLETE")
    print("=" * 100)

if __name__ == "__main__":
    main()

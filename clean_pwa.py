import pandas as pd
import re

df = pd.read_csv('data/raw/athletes/pwa_athletes_raw.csv')
print(f'PWA raw: {len(df)} athletes')

orig = len(df)
df['name'] = df['name'].astype(str).apply(lambda x: re.sub(r'\s+', ' ', x).strip())
df = df[df['name'].notna()]
df = df[df['name'].str.lower() != 'nan']
df['sail_number'] = df['sail_number'].astype(str)
df = df[df['sail_number'].str.contains(r'\d', na=False)]
unwanted = ['CRO-751', 'E-4', 'SGP-21']
df = df[~df['sail_number'].isin(unwanted)]
df = df[(df['name'] != 'Marc') & (df['name'] != 'Farrah Hall')]
df.loc[df['name'] == 'Julian Salmonn', 'sail_number'] = 'G-901'

df.to_csv('data/raw/athletes/pwa_athletes_clean.csv', index=False)
print(f'PWA clean: {len(df)} athletes (removed {orig-len(df)})')
print("\nPhase 2A & 2B COMPLETE!")
print("=" * 50)
print(f"PWA: {len(df)} athletes")
lh = pd.read_csv('data/raw/athletes/liveheats_athletes_clean.csv')
print(f"LiveHeats: {len(lh)} athletes")
print(f"Total: {len(df) + len(lh)} athletes ready for matching")

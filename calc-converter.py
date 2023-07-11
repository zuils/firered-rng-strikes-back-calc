import requests
import re
import json
import pathlib
from math import floor

response = requests.get("https://raw.githubusercontent.com/pret/pokefirered/master/src/data/trainer_parties.h")
trainers_content = response.text

pokedex_response = requests.get("https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/pokedex.ts")
pokedex_content = pokedex_response.text

species_sections = re.findall(r"([a-z]+): {\s*num:.*?abilities: {(.*?)},", pokedex_content, re.DOTALL)

with open("C:/Users/vijay/Downloads/Pokemon-Learnsets/output/gen3.json") as file:
    learnsets = json.load(file)

moves_content = pathlib.Path(
    "C:/Users/vijay/firered-rng-strikes-back-calc/calc/src/data/moves.ts"
).read_text()

beginning = "'(No Move)': {bp: 0, category: 'Status', type: 'Normal'},"
end = "'Vital Throw': {bp: 70, type: 'Fighting'},"
beginningIndex = moves_content.index(beginning)
endIndex = moves_content.index(end)
moves = moves_content[beginningIndex:endIndex + len(end)]
moves = re.sub(r":.*", "", moves)
moves = re.sub(r"};\n\nconst GSC_PATCH", "", moves)
moves = re.sub(r"\n\s*\n", "\n", moves)
moves = re.sub(r"\n\s+", "\n", moves)
movesFormat = [str(move).replace("'", "") for move in moves.splitlines()]

cutoff = "// Start of actual trainer data"
index = trainers_content.find(cutoff)
teams_data = trainers_content[index + len(cutoff):]

# Extract the trainer party sections from the trainers_content using regular expressions
party_sections = re.findall(r"static const struct TrainerMon(.*?) (.*?)\[\] = {(.*?)};", trainers_content, re.DOTALL)

species_sections = re.findall(r"([a-z]+): {\s*num:.*?abilities: {(.*?)},", pokedex_content, re.DOTALL)

# Initialize an empty dictionary
species_data = {}

# Process each species section and populate the dictionary
for section in species_sections:
    species_name = section[0]  # Extract the species name
    abilities_data = section[1]  # Extract the abilities data
    index = abilities_data.find(",")
    if index != -1:
        abilities_data = abilities_data[:index]
    if ability_match := re.search(r"0: \"(.*?)\"", abilities_data):
        ability = ability_match[1]
    else:
        ability = ""

    species_data[species_name] = ability

# Initialize an empty dictionary
trainer_parties = {}

# Process each party section and populate the dictionary
for section in party_sections:
    party_type = section[0]  # Extract the party type (ItemDefaultMoves or ItemCustomMoves)
    party_name = section[1]  # Extract the party name
    pokemon_data = section[2]  # Extract the Pokemon data

    # Extract the relevant information for each Pokemon in the party
    pokemon_list = re.findall(r"{(.*?)}", pokemon_data, re.DOTALL)

    # Initialize a list to store the party data
    party = []

    # Process each Pokemon data and create a dictionary for it
    for pokemon_str in pokemon_list:
        pokemon_info = {}
        key_value_pairs = pokemon_str.split(",\n")

        # Extract the IV, level, species, and held item information for the Pokemon
        for pair in key_value_pairs:
            if "=" in pair:
                key, value = pair.strip().split("=")
                key = key.strip().strip(".")
                value = value.strip()

                if key == "species":
                    value = value.replace("SPECIES_", "").title().replace("_", " ")

                if key == "heldItem":
                    value = value.replace("ITEM_", "").title().replace("_", " ")

                # Convert numerical values to integers
                if key in "iv":
                    value = floor(int(value) * 31 / 255)

                if key in "lvl":
                    value = int(value)

                pokemon_info[key] = value
            else:
                moves_list = pair.strip().strip("{ }").split(", ")
                moves_list = [move.strip().replace("MOVE_", "") for move in moves_list]
                pokemon_info["moves"] = moves_list

        # Get the ability information from the species_data dictionary
        species_name = pokemon_info["species"]
        #print(species_name)
        ability = species_data.get(species_name)
        #print(ability)
        pokemon_info["ability"] = ability
        #print(pokemon_info["ability"])

        party.append(pokemon_info)

    # Add the party to the dictionary
    trainer_parties[party_name] = (party_type, party)

# Iterate over trainer parties
for party_type, party in trainer_parties.values():
    for pokemon in party:
        species_name = pokemon["species"].lower().replace("_", "")
        pokemon["ability"] = species_data.get(species_name, "")
        #print(pokemon["ability"])

# Iterate over trainer parties
for party in trainer_parties.values():
    # Check if the party type is ItemDefaultMoves
    if party and "DefaultMoves" in party[0]:
        # Process each Pokemon in the party
        for pokemon in party[1]:
            species_name = pokemon["species"]
            species_moves = learnsets.get(species_name.lower().replace(" ", ""), {})
            pokemon_moves = []

            # Retrieve moves based on the Pokemon's level
            for level in range(1, pokemon['lvl'] + 1):
                if move := species_moves.get(str(level)):
                    pokemon_moves.append(move)

            # Update the Pokemon's moves to only include the last four moves
            pokemon["moves"] = pokemon_moves[-4:]

# Convert the moves to a consistent format
for party in trainer_parties.values():
    for pokemon in party[1]:
        moves = pokemon.get("moves")
        if moves and isinstance(moves, str):
            moves = moves.strip("{}").split(", ")
            moves = [move.replace("MOVE_", "") for move in moves]
            pokemon["moves"] = moves

new_trainer_parties = {}

for party_name, (party_type, party) in trainer_parties.items():
    if party:
        # Split the party name whenever there is a capital letter or number
        party_name = party_name.replace("sParty_", "")
        stripped_party_name = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', party_name)
        new_trainer_parties[stripped_party_name] = party

'''
# Print the modified new_trainer_parties dictionary
with open('test.json', 'w') as f:
    f.write(json.dumps(new_trainer_parties, indent=4))
'''

output_data = {}

# Iterate over trainer parties
for party_name, (party_type, party) in trainer_parties.items():
    for pokemon in party:
        species_name = pokemon["species"]
        ability = pokemon["ability"]
        moves = pokemon["moves"]

        # Create the Pokemon entry
        pokemon_entry = {
            "level": pokemon["lvl"],
            "ability": ability,
            "item": pokemon.get("heldItem", ""),
            "moves": moves
        }

        # Format the trainer name
        party_name = party_name.replace("sParty_", "")
        stripped_party_name = re.sub(r'(?<=[a-z])(?=[A-Z0-9])', ' ', party_name)

        # Check if the IVs are specified for the Pokemon
        if "iv" in pokemon:
            # Retrieve the IV values from the Pokemon data
            iv_values = {
                "hp": pokemon["iv"],
                "at": pokemon["iv"],
                "df": pokemon["iv"],
                "sa": pokemon["iv"],
                "sd": pokemon["iv"],
                "sp": pokemon["iv"]
            }

        # Add the ivs entry to the Pokemon entry
        pokemon_entry["ivs"] = iv_values

        if isinstance(moves, list):
            formatted_moves = []
            for move in moves:
                formatted_move = move.title().replace("_", " ")
                for mv in movesFormat:
                    if formatted_move.lower() == mv.lower().replace(" ", ""):
                        formatted_move = mv                
                formatted_moves.append(formatted_move)
            pokemon_entry["moves"] = formatted_moves


        # Create the trainer entry if it doesn't exist
        if species_name not in output_data:
            output_data[species_name] = {}

        # Add the Pokemon entry to the trainer's party
        output_data[species_name][stripped_party_name] = pokemon_entry

# Convert the moves to a consistent format
for party in trainer_parties.values():
    for pokemon in party[1]:
        moves = pokemon.get("moves")
        if moves and isinstance(moves, list):
            formatted_moves = [move.title() for move in moves]
            pokemon["moves"] = formatted_moves


# Write the output data to the file
with open('test.json', 'w') as f:
    f.write(json.dumps(output_data, indent=4))

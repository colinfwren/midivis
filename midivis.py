import midi
import math
import argparse
from collections import OrderedDict

parser = argparse.ArgumentParser(description="Turn a .midi file into a graph")
parser.add_argument('midi_file', help='Path to .midi file to process')

args = parser.parse_args()

song = midi.read_midifile(args.midi_file)
song.make_ticks_abs()
track = song[0]
crotchet = song.resolution
quaver = crotchet / 2
semi_quaver = quaver / 2
demi_quaver = semi_quaver / 2
phrases = []
chains = 0
notes_at_tick = {}
note_names = {v: k for k, v in midi.NOTE_NAME_MAP_SHARP.items()}
drum_names = {
    'C_3': 'BD-',
    'B_3': 'MT-',
    'A_3': 'MT-',
    'G_3': 'LT-',
    'Gs_3': 'CHH',
    'D_3': 'SD-',
    'Cs_4': 'CYM',
    'C_4': 'HT-',
    'Ds_4': 'RCY',
    'D_4': 'HT-',
    'E_4': 'RCY'
}


class Phrase:

    def __init__(self, note_count, start_tick, end_tick, label, notes):
        self.note_count = note_count
        self.start_tick = start_tick
        self.end_tick = end_tick
        self.label = label
        self.__notes = notes

    @property
    def notes(self):
        phrase_notes = [pos_note_pair[1] for pos_note_pair in self.__notes.items()]
        notes = [[note_names[note.pitch] for note in notes] for notes in phrase_notes]
        if len(notes) < 16:
            notes.append(['H00'])
        return notes


# Get time signature events
time_sigs = [tick for tick in track if tick.name == 'Time Signature']
tempos = [tick for tick in track if tick.name == 'Set Tempo']
notes = [tick for tick in track if tick.name == 'Note On']
end_of_song = [tick for tick in track if tick.name == 'End of Track'][0]
for tick in range(0, (end_of_song.tick + semi_quaver), semi_quaver):
    notes_at_tick[tick] = []

for index, note in enumerate(notes):
    next_note = notes[index+1] if index != (len(notes)-1) else end_of_song
    note_delta = next_note.tick - note.tick
    if note_delta % semi_quaver == 0:
        notes_at_tick[note.tick].append(note)

processed_notes = OrderedDict(sorted(notes_at_tick.items(), key=lambda t: t[0]))

for index, time_sig in enumerate(time_sigs):
    next_time_sig = time_sigs[index + 1] if index != (len(time_sigs) - 1) else end_of_song
    fraction_resolution = 16 / time_sig.denominator
    notes_per_phrase = (time_sig.numerator * fraction_resolution)
    time_sig_length = next_time_sig.tick - time_sig.tick
    time_sig_bars = time_sig_length / (notes_per_phrase * semi_quaver)
    for phrase_index in range(0, time_sig_bars):
        start_tick = time_sig.tick + (phrase_index * (notes_per_phrase * semi_quaver))
        end_tick = start_tick + (notes_per_phrase * semi_quaver)
        phrase_count = int(math.ceil(notes_per_phrase / 16)) + 1
        if phrase_count > 1:
            for offset_index, phrase in enumerate(range(0, phrase_count)):
                end_offset = end_tick - ((notes_per_phrase % 16) * semi_quaver)
                new_start_tick = start_tick if offset_index == 0 else end_offset
                new_end_tick = end_offset if offset_index == 0 else end_tick
                note_count = 16 if offset_index == 0 else (notes_per_phrase % 16)
                note_range = range(new_start_tick, new_end_tick, 120)
                phrase_notes = {k: processed_notes[k] for k in note_range}
                notes = OrderedDict(sorted(phrase_notes.items(), key=lambda t: t[0]))
                phrases.append(
                    Phrase(
                        note_count,
                        new_start_tick,
                        new_end_tick,
                        '{0}/{1}'.format(time_sig.numerator, time_sig.denominator),
                        notes
                    )
                )
        else:
            note_range = range(start_tick, end_tick, 120)
            phrase_notes = {k: processed_notes[k] for k in note_range}
            notes = OrderedDict(sorted(phrase_notes.items(), key=lambda t: t[0]))
            phrases.append(
                Phrase(
                    notes_per_phrase,
                    start_tick,
                    end_tick,
                    '{0}/{1}'.format(time_sig.numerator, time_sig.denominator),
                    notes
                )
            )


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def safe_list_get(l, idx):
    try:
        return l[idx]
    except IndexError:
        return '---'


def get_drum_name(name):
    if name == '---':
        return name
    return drum_names[name]

chains = list(chunks(phrases, 10))


def print_drums(notes):
    """ Print out a LSDJ phrase notes """
    row_template = '{note_num}{drum_1}  {drum_2}  {cmd}'
    rows = []
    for index, row in enumerate(notes):
        drums = [note for note in row if note in drum_names.keys()]
        drum_1 = safe_list_get(drums, 0)
        drum_2 = safe_list_get(drums, 1)
        cmds = [note for note in row if note in ['H00']]
        cmd = safe_list_get(cmds, 0)
        rows.append(row_template.format(
            note_num='{:x}'.format(index).ljust(4),
            drum_1=get_drum_name(drum_1),
            drum_2=get_drum_name(drum_2),
            cmd=cmd
        ))
    return '\n'.join(rows)

print(phrases[0].notes)
print(print_drums(phrases[1].notes))

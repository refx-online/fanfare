from __future__ import annotations

import app
from app.packets import BanchoPacketReader
from app.packets import BasePacket
from app.usecases.performance import calculate_accuracy


class MatchScoreUpdate(BasePacket):
    def __init__(self, reader: BanchoPacketReader):
        self.play_data = reader.read_scoreframe()

    async def handle(self, player):
        match = player.match
        if match is None:
            return

        slot_id = match.get_slot_id(player)
        if slot_id is None:
            return

        sf = self.play_data
        if match.pp_competition:
            slot_mods = match.slots[slot_id].mods | match.mods
            passed_objects = sf.num300 + sf.num100 + sf.num50 + sf.num_miss
            accuracy = calculate_accuracy(
                mode_vn=match.mode,
                n300=sf.num300,
                n100=sf.num100,
                n50=sf.num50,
                nmiss=sf.num_miss,
                nkatu=sf.num_katu,
                ngeki=sf.num_geki,
                score_v2=sf.score_v2,
            )
            performance = await app.state.services.performance_service.calculate_performance_single(
                beatmap_id=match.map_id,
                mode=match.mode,
                mods=slot_mods,
                max_combo=sf.max_combo,
                accuracy=accuracy,
                miss_count=sf.num_miss,
                passed_objects=passed_objects,
            )
            total_score = int(performance.pp)
        else:
            total_score = sf.total_score

        score_frame_packet = app.packets.ScoreFrame(
            time=sf.time,
            id=slot_id,
            num300=sf.num300,
            num100=sf.num100,
            num50=sf.num50,
            num_geki=sf.num_geki,
            num_katu=sf.num_katu,
            num_miss=sf.num_miss,
            total_score=total_score,
            max_combo=sf.max_combo,
            current_combo=sf.current_combo,
            perfect=sf.perfect,
            current_hp=sf.current_hp,
            tag_byte=sf.tag_byte,
            score_v2=sf.score_v2,
            combo_portion=sf.combo_portion if sf.score_v2 else None,
            bonus_portion=sf.bonus_portion if sf.score_v2 else None,
        )

        match.enqueue(
            app.packets.match_score_update(score_frame_packet),
            lobby=False,
        )

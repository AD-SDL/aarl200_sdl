def assign_timestamps(protocol, tube_rack_info):
    for step in protocol.actions:
        if step.action_type == "transfer":
            target_well = step.target_well
            if target_well in tube_rack_info:
                tube_info = tube_rack_info[target_well]
                tube_info.sampled_at = step.aspirate_timestamp
            
    return tube_rack_info
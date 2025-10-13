from opentrons import protocol_api
from opentrons import types

metadata = {'protocolName': 'QIASeq FX v1.0 6-24-25','author': 'UCR exFAB','source': 'Modified from Opentrons Protocol Library',}
requirements = {"robotType": "Flex","apiLevel": "2.18",}

def add_parameters(parameters):
    # ======================== RUNTIME PARAMETERS ========================
    parameters.add_bool(
        display_name="Dry Run",
        variable_name="DRYRUN",
        default=False,
        description="Whether to perform a dry run or not.")
    parameters.add_int(
        display_name="Percent reaction",
        variable_name="REACTIONPERCENT",
        default=100,minimum=40,maximum=100,
        description="Percent of reaction reagents to use")
    parameters.add_int(
        display_name="Fragmentation Time (Min)",
        variable_name="FRAGTIME",
        default=9,minimum=6,maximum=30,
        description="Length of Fragmentation Incubation.")
    parameters.add_int(
        display_name="PCR Cycles",
        variable_name="PCRCYCLES",
        default=9,minimum=1,maximum=12,
        description="How many PCR Cycles to for amplification.")
    parameters.add_int(
        display_name="Final elution volumen",
        variable_name="FELUTION",
        default=35, minimum=10,maximum=50,
        description="Set final elution volume in uL")

def run(protocol: protocol_api.ProtocolContext):
    # ======================== DOWNLOADED PARAMETERS ========================
    global USE_GRIPPER              # T/F Whether or not Using the Gripper
    global COLUMNS                  # Number of Columns of Samples
    global WASTEVOL                 # Number - Total volume of Discarded Liquid Waste
    global ETOHVOL                  # Number - Total volume of Available EtOH
    global Liquid_trash             # Which well to dispense trash liquid
    # =================== LOADING THE RUNTIME PARAMETERS ==================== 
    DRYRUN              = protocol.params.DRYRUN
    REACTIONPERCENT     = protocol.params.REACTIONPERCENT
    COLUMNS             = 6
    FRAGTIME            = protocol.params.FRAGTIME
    PCRCYCLES           = protocol.params.PCRCYCLES
    FELUTION            = protocol.params.FELUTION
    # =================================================================================================
    # ====================================== ADVANCED PARAMETERS ======================================
    # =================================================================================================
    #-------PROTOCOL STEP-------
    STEP_FXENZ            = True     # Set to 0 to skip block of commands
    STEP_LIG              = True     # Set to 0 to skip block of commands
    STEP_CLEANUP_1        = True     # Set to 0 to skip block of commands
    STEP_PCR              = True    # Set to 0 to skip block of commands
    STEP_CLEANUP_3        = True     # Set to 0 to skip block of commands
    STEP_NORMALIZE        = 0     # Set to 0 to skip block of commands
    DIAGNOSTIC            = True     # Set to 0 to skip block of commands
    #---------------------------
    DEACTIVATE_TEMP       = True      # Default True    | True = Temp and / or Thermocycler deactivate at end of run, False = remain on, such as leaving at 4 degrees
    USE_GRIPPER           = True      # Default True    | True = Uses the FLEX Gripper, False = No Gripper Movement, protocol pauses and requires manual intervention.    
    # ======================== BACKGROUND PARAMETERS ========================
    WASTEVOL            = 0         # Number - Total volume of Discarded Liquid Waste
    ETOHVOL             = 0         # Number - Total volume of Available EtOH    
    # =============================== PIPETTE ===============================
    p1000 = protocol.load_instrument('flex_8channel_1000', 'left')
    p50   = protocol.load_instrument("flex_8channel_50", "right")
    # ========================= PIPETTE SETTINGS ============================
    p1000_flow_rate_aspirate_default = 200
    p1000_flow_rate_dispense_default = 200
    p1000_flow_rate_blow_out_default = 400
    p1000_mix_flow_rate = 0.5                       
    p50_flow_rate_aspirate_default = 50
    p50_flow_rate_dispense_default = 50
    p50_flow_rate_blow_out_default = 100
    p50_mix_flow_rate = 0.5                             
    # ============================== OFFSETS ==================================
    PCRPlate_Thermocycler_Z_offset = 0.5 
    PCRPlate_Temperature_Z_offset  = 0.5
    Deepwell_HeaterShaker_Z_offset = 0.75
    Deepwell_MagBlock_Z_offset     = 0.75
    Deepwell_Deck_Z_offset         = 0.75 
    #========================== CODE BLOCKS USED MULTIPLE TIMES IN PROTOCOL=================================
    
    def move_labware(labware, new_location, R):
        if R == 'ye':
            heatershaker.open_labware_latch()
            protocol.move_labware(labware,new_location,use_gripper=USE_GRIPPER)
            heatershaker.close_labware_latch()
        else:
            protocol.move_labware(labware,new_location,use_gripper=USE_GRIPPER)
        
    def waste_volume_check(Sup):
        global WASTEVOL
        global Liquid_trash
        WASTEVOL+=(Sup*8)
        if WASTEVOL <14400:
            Liquid_trash = Liquid_trash_well_1
            return Liquid_trash
        if WASTEVOL >=14400 and WASTEVOL <28800:
            Liquid_trash = Liquid_trash_well_2
            return Liquid_trash
        if WASTEVOL >=28800 and WASTEVOL < 43200:
            Liquid_trash = Liquid_trash_well_3
            return Liquid_trash
        if WASTEVOL >= 43200:
            Liquid_trash_well_4 = reservoir['A9']
            Liquid_trash = Liquid_trash_well_4
            return Liquid_trash
        
    def add_fragmentation_mix(vol, mix_vol, mix_rep, source_plate, destination_plate, destination_well):
        p50.aspirate(vol+1, source_plate.bottom(z=PCRPlate_Temperature_Z_offset))
        p50.dispense(1, source_plate.bottom(z=PCRPlate_Temperature_Z_offset))
        p50.dispense(vol, destination_plate.wells_by_name()[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset))
        p50.mix(mix_rep,mix_vol, rate = p50_mix_flow_rate)
        p50.move_to(destination_plate[destination_well].top(z=-3))
        protocol.delay(seconds=3)
        p50.blow_out(destination_plate[destination_well].top(z=-3))

    def add_barcodes(vol, mix_rep, mix_vol, source_plate, source_well, destination_plate, destination_well):
        p50.aspirate(vol+1, source_plate.wells_by_name()[source_well].bottom(z=PCRPlate_Temperature_Z_offset ))
        p50.dispense(1, source_plate.wells_by_name()[source_well].bottom(z=PCRPlate_Temperature_Z_offset ))
        p50.dispense(vol, destination_plate.wells_by_name()[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset))
        p50.mix(mix_rep,mix_vol, rate = p50_mix_flow_rate)
        p50.move_to(destination_plate[destination_well].top(z=-3))
        protocol.delay(seconds=3)
        p50.blow_out(destination_plate[destination_well].top(z=-3))
        
    def add_ligation_mix(vol, mix_rep, mix_vol, source_plate, source_well, destination_plate, destination_well, offset):
        p50.move_to(source_plate.wells_by_name()[source_well].bottom(z=PCRPlate_Temperature_Z_offset+1.5))
        p50.mix(mix_rep,mix_vol/4, rate = p50_mix_flow_rate/4)
        p50.aspirate(vol+2, source_plate.wells_by_name()[source_well].bottom(z=offset), rate = p50_mix_flow_rate/4)
        p50.dispense(2, source_plate.wells_by_name()[source_well].bottom(z=PCRPlate_Temperature_Z_offset), rate=p50_mix_flow_rate/4)
        p50.default_speed = 100
        p50.move_to(source_plate.wells_by_name()[source_well].top(z=5))
        protocol.delay(seconds=1)
        p50.default_speed = 400
        p50.dispense(vol, destination_plate[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset), rate = p50_mix_flow_rate/4)
        p50.move_to(destination_plate[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset+1))
        p50.mix(mix_rep,mix_vol, rate= p50_mix_flow_rate/4)
        p50.default_speed = 100
        p50.move_to(sample_plate_1[destination_well].top(z=-3))
        protocol.delay(seconds=3)
        p50.blow_out(sample_plate_1[destination_well].top(z=-3))
        p50.default_speed = 400
        
    def add_water(vol,source_plate,destination_plate,destination_well):
        p1000.aspirate(vol, source_plate.bottom(z=Deepwell_Deck_Z_offset))
        p1000.move_to(destination_plate[destination_well].top(z=-3))
        p1000.dispense(vol, destination_plate[destination_well])

    def add_beads(vol,mix_rep,source_plate,destination_plate,destination_well):
        if STEP_CLEANUP_1 == True:
            protocol.comment('--> Adding CleanupBead (0.75x)')
        else:
            protocol.comment('--> Adding CleanupBead (1.0x)')
        p1000.mix(mix_rep,vol+3, source_plate.bottom(z=Deepwell_Deck_Z_offset), rate = p1000_mix_flow_rate/2) # Adding Extra offset to the bead aspiration
        p1000.aspirate(vol+3, source_plate.bottom(z=Deepwell_Deck_Z_offset))
        p1000.dispense(3, source_plate.bottom(z=Deepwell_Deck_Z_offset))
        p1000.default_speed = 100
        p1000.move_to(source_plate.top(z=-3))
        p1000.dispense(vol, destination_plate[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset))
        p1000.touch_tip()
        
    def add_sample(vol, source_plate,destination_plate,source_well,destination_well):
        protocol.comment('--> Transferring Samples')
        p1000.move_to(source_plate[source_well].bottom(z=PCRPlate_Thermocycler_Z_offset)) # Extra Offset Added for full sample
        p1000.aspirate(vol, rate =0.5)
        p1000.dispense(vol, destination_plate[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset))
        
    def bead_mixing(destination_plate,destination_well):
        protocol.comment('mixing beads')
        p1000.default_speed = 100
        p1000.move_to(destination_plate[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset+0.5))
        CleanupBeadMix = 2
        for Mix in range(CleanupBeadMix):
            p1000.aspirate(70, rate=0.5)
            p1000.move_to(destination_plate[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset+0.5))
            p1000.aspirate(20, rate=0.5)
            p1000.dispense(20, rate=0.5)
            p1000.move_to(destination_plate[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset+0.5))
            p1000.dispense(70, rate=0.5)
            Mix += 1
        p1000.move_to(destination_plate[destination_well].top(z=-3))
        protocol.delay(seconds=1)
        p1000.blow_out(destination_plate[destination_well].top(z=-3))
        p1000.touch_tip(speed=100)
        p1000.default_speed = 400
        p1000.move_to(destination_plate[destination_well].top(z=5))
        p1000.move_to(destination_plate[destination_well].top(z=0))
        p1000.move_to(destination_plate[destination_well].top(z=5))
        p1000.default_speed = 400
        
    def remove_supernatant(pipette,delay,vol,vol2,source_plate,source_well):
        pipette.move_to(source_plate[source_well].bottom(z=Deepwell_MagBlock_Z_offset))
        pipette.aspirate(vol-(vol/2))
        protocol.delay(seconds=delay)
        pipette.move_to(source_plate[source_well].bottom(z=Deepwell_MagBlock_Z_offset))
        pipette.aspirate(vol/2)
        pipette.default_speed = 200
        pipette.move_to(source_plate[source_well].top(z=2))
        if delay == 3:
            pipette.touch_tip(speed=100)
        #======L Waste Volume Check======
        waste_volume_check(vol2)
        #================================ 
        pipette.dispense(vol, Liquid_trash.top(z=0))
        protocol.delay(seconds=delay)
        pipette.blow_out()
        if delay == 3:
            pipette.touch_tip()
        pipette.default_speed = 400
        pipette.move_to(Liquid_trash.top(z=-5))
        pipette.move_to(Liquid_trash.top(z=0))
        
    def ethanol_wash(vol,source_plate,source_well,destination_plate,destination_well):       
        p1000.aspirate(vol, source_plate.wells_by_name()[source_well].bottom(z=Deepwell_Deck_Z_offset), rate=0.5)
        p1000.move_to(source_plate.wells_by_name()[source_well].top(z=0))
        p1000.move_to(source_plate.wells_by_name()[source_well].top(z=-5))    
        #==========Tip Touch============
        p1000.touch_tip()
        #================================ 
        p1000.move_to(destination_plate[destination_well].top(z=2))
        p1000.dispense(vol, rate=0.75)
        protocol.delay(seconds=2)
        p1000.blow_out(destination_plate[destination_well].top(z=0))
        p1000.move_to(destination_plate[destination_well].top(z=5))
        p1000.move_to(destination_plate[destination_well].top(z=0))
        p1000.move_to(destination_plate[destination_well].top(z=5))          
      
    def remove_ethanol(vol,source_plate,source_well):
            p1000.move_to(source_plate[source_well].bottom(z=Deepwell_MagBlock_Z_offset))
            p1000.aspirate(vol-100)
            protocol.delay(seconds=3)
            p1000.move_to(source_plate[source_well].bottom(z=Deepwell_MagBlock_Z_offset))
            p1000.aspirate(100)
            p1000.default_speed = 100
            p1000.move_to(source_plate[source_well].top(z=-2))
            p1000.default_speed = 200
            p1000.touch_tip(speed=100)
            #======L Waste Volume Check======
            waste_volume_check(vol)
            #================================ 
            p1000.dispense(200, Liquid_trash.top(z=-3))
            protocol.delay(seconds=2)
            p1000.blow_out()
            #=====Reservoir Tip Touch========
            p1000.touch_tip()
            #================================
            p1000.move_to(Liquid_trash.top(z=-5))
            p1000.move_to(Liquid_trash.top(z=0))

    def add_resuspension_buffer(vol,source_plate,destination_plate,destination_well):
        p50.aspirate(vol, source_plate.bottom(z=Deepwell_Deck_Z_offset), rate = 0.5)
        p50.move_to(destination_plate.wells_by_name()[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset))
        p50.dispense(vol,destination_plate.wells_by_name()[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset), rate=0.5)
        RSBMix = 2
        for Mix in range(RSBMix):
            p50.aspirate(vol/2, destination_plate.wells_by_name()[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset+1), rate=0.5)
            p50.dispense(vol/2, destination_plate.wells_by_name()[destination_well].bottom(z=Deepwell_HeaterShaker_Z_offset+1), rate=1)
        p50.blow_out(destination_plate.wells_by_name()[destination_well].top(z=-3))

    def move_primers(vol,source_plate,destination_plate,destination_well):
        p50.aspirate(vol,source_plate.bottom(z=PCRPlate_Temperature_Z_offset))
        p50.dispense(vol,destination_plate[destination_well].bottom(PCRPlate_Thermocycler_Z_offset))
        
    def transfer_supernatant(vol,source_plate,source_well,destination_plate,destination_well,PCR):
        if PCR == 'yes':
            move_primers(vol/4,Primer,destination_plate,destination_well)
        p50.move_to(source_plate[source_well].bottom(z=Deepwell_MagBlock_Z_offset))
        p50.aspirate(vol, rate =0.5)
        p50.dispense(vol, destination_plate[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset), rate=0.5)
        if PCR == 'yes':
            p50.mix(2,vol/2,rate=0.5)

    def add_PCR_mix(vol,vol2,mix_rep,mix_rep2,destination_plate,destination_well):
        p50.mix(mix_rep,vol/2, PCR.bottom(z=PCRPlate_Temperature_Z_offset+1), rate = p50_mix_flow_rate)
        p50.aspirate(vol, PCR.bottom(z=PCRPlate_Temperature_Z_offset))
        p50.dispense(vol, destination_plate[destination_well].bottom(z=PCRPlate_Thermocycler_Z_offset))
        p50.mix(mix_rep2, vol2, rate=0.5)
        p50.move_to(destination_plate[destination_well].top(z=-3))
        protocol.delay(seconds=3)
        p50.blow_out(destination_plate[destination_well].top(z=-3))
    
    def transfer_and_blowout(pipette, vol, source_plate, source_offset, destination_plate, destination_well, destination_offset, rate):
        pipette.aspirate(vol, source_plate.bottom(z=source_offset), rate=rate)
        pipette.dispense(vol, destination_plate[destination_well].bottom(z=destination_offset))
        pipette.blow_out(destination_plate[destination_well].top(z=-3))
    
    def normalization_wash(pipette, vol, Wash_well, destination_plate, destination_well):
        pipette.move_to(WashPlate[Wash_well].bottom(z=PCRPlate_Thermocycler_Z_offset+0.5))
        pipette.aspirate(vol/2, rate = 0.25)
        protocol.delay(seconds=0.2)
        pipette.aspirate(vol/2, rate = 0.25)
        pipette.dispense(vol, destination_plate[destination_well].top(z=-3), rate=0.6)
    
    # ======================= DECK SETUP ======================
    # ========== FIRST ROW ===========
    thermocycler    = protocol.load_module('thermocycler module gen2')
    sample_plate_1  = thermocycler.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'Sample Plate 1')
    tiprack_200_1   = protocol.load_labware('opentrons_flex_96_filtertiprack_200ul','A2','tiprack_200_1')
    tiprack_200_R   = protocol.load_labware('opentrons_flex_96_filtertiprack_200ul','A3','tiprack_200_R')
    sample_plate_2  = protocol.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt','A4','Sample Plate 2')
    # ========== SECOND ROW ==========
    tiprack_50_1    = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul','B2','tiprack_50_1')
    tiprack_50_R    = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul','B3','tiprack_50_R')
    tiprack_50_2    = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul','B4','tiprack_50_2')
    # ========== THIRD ROW ===========
    temp_block      = protocol.load_module('temperature module gen2', 'C1')
    temp_adapter    = temp_block.load_adapter('opentrons_96_well_aluminum_block')
    reagent_plate_1 = temp_adapter.load_labware('opentrons_96_wellplate_200ul_pcr_full_skirt', 'Reagent Plate')
    reservoir       =  protocol.load_labware('nest_96_wellplate_2ml_deep','C2', 'Reservoir Plate')
    tiprack_50_3    = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul','C3','tiprack_50_3')
    tiprack_50_4    = protocol.load_labware('opentrons_flex_96_filtertiprack_50ul','C4','tiprack_50_4')
    # ========== FOURTH ROW ==========
    heatershaker    = protocol.load_module('heaterShakerModuleV1','D1')
    CleanupPlate_1  = heatershaker.load_labware('nest_96_wellplate_2ml_deep', 'Cleanup Plate')
    mag_block       = protocol.load_module('magneticBlockV1', 'D2')
    TRASH           = protocol.load_waste_chute() #Trash chute on D3
    #CleanupPlate_2  = protocol.load_labware('nest_96_wellplate_2ml_deep','D4','CleanupPlate_2')
    # ========================== REAGENT PLATE_1 ============================
    FXENZ               = reagent_plate_1['A1']
    LIG1                = reagent_plate_1['A2']
    LIG2                = reagent_plate_1['A3']  
    Primer              = reagent_plate_1['A4']
    PCR                 = reagent_plate_1['A5']
    NormBead            = reagent_plate_1['A6']
    Barcodes_1          = reagent_plate_1['A7']
    Barcodes_2          = reagent_plate_1['A8']
    Barcodes_3          = reagent_plate_1['A9']  
    Barcodes_4          = reagent_plate_1['A10'] 
    Barcodes_5          = reagent_plate_1['A11'] 
    Barcodes_6          = reagent_plate_1['A12'] 
    # ============================ RESERVOIR ================================
    CleanupBead           = reservoir['A1']    
    RSB                   = reservoir['A2']
    NormElute             = reservoir['A3']           
    EtOH_1                = reservoir['A4']
    EtOH_2                = reservoir['A5']  
    EtOH_3                = reservoir['A6']  
    #N/A                  = reservoir['A7'] 
    #N/A                  = reservoir['A8'] 
    Water                 = reservoir['A9']
    Liquid_trash_well_3   = reservoir['A10'] 
    Liquid_trash_well_2   = reservoir['A11'] 
    Liquid_trash_well_1   = reservoir['A12']
    # ======================= SAMPLE TRACKING ===============================
    # This the math needed to generate lists of wells for the pipette to loop through.
    add = 5
    #Sample Volumes
    reduction = (REACTIONPERCENT/100)
    PCRrx       = 50 * reduction
    #FX
    FXvol     = 15        * reduction
    FXmixvol  = (50       * reduction)/2
    Ligvol    = (REACTIONPERCENT/2)-5
    Ligmixvol = (REACTIONPERCENT)/2
    Resusup_1 = PCRrx       * .4     
    PCRmixvol = PCRrx/2
    Water_1   = 100 - (100 * reduction)
    Water_2   = 50 - (50   * reduction)
    # ============================ OFFSETS ===========================
    # These are Offsets which are a PER INSTRUMENT Setting, to account for slight adjustments of the gripper calibration or labware.
    gripper_offset={'x':0,'y':0,'z':0}
    # =========  Default Flow rates ==========================    
    p50.flow_rate.aspirate = p50_flow_rate_aspirate_default*0.5
    p50.flow_rate.dispense = p50_flow_rate_dispense_default*0.5
    p50.flow_rate.blow_out = p50_flow_rate_blow_out_default*0.5
    p1000.flow_rate.aspirate = p1000_flow_rate_aspirate_default*0.5
    p1000.flow_rate.dispense = p1000_flow_rate_dispense_default*0.5
    p1000.flow_rate.blow_out = p1000_flow_rate_blow_out_default*0.5
    # =================================================================================================
    # ========================================= PROTOCOL START ========================================
    # =================================================================================================
    thermocycler.open_lid()
    heatershaker.open_labware_latch()
    if DRYRUN == False:
        protocol.comment("SETTING THERMO and TEMP BLOCK Temperature")
        thermocycler.set_block_temperature(4)
        thermocycler.set_lid_temperature(70)    
        temp_block.set_temperature(4)
        protocol.pause("Ready")
    heatershaker.close_labware_latch() 
    # =================================================================================================
    # ========================================= PROTOCOL START ========================================
    # =================================================================================================
################################################################################################    
    #Section 1 -- Fragmentation   
    if STEP_FXENZ == True:
        protocol.comment('==============================================')
        protocol.comment('--> FX')
        protocol.comment('==============================================')
        protocol.comment('')
        if DIAGNOSTIC == True:
            print('Adding FX')
        # ============ Steps 1 - 7 =====================
        for x in range(COLUMNS):
            Target_column = 'A'+str(x+1)
            print(Target_column+' from tiprack_50_1')
            p50.pick_up_tip(tiprack_50_1.wells_by_name()[Target_column])
            add_fragmentation_mix(FXvol,FXmixvol,20,FXENZ,sample_plate_1,Target_column)
            p50.drop_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p50_1')
            print('There are '+ str(12-(COLUMNS))+' left in p50_1')
        # ============== End Section =================
        # ============ Steps 8-10 ======================       
        if DRYRUN == False:
            thermocycler.close_lid()
            profile_FXENZ = [
                {'temperature': 32, 'hold_time_minutes': FRAGTIME},
                {'temperature': 65, 'hold_time_minutes': 30}
                ]
            thermocycler.execute_profile(steps=profile_FXENZ, repetitions=1, block_max_volume=50)
            thermocycler.set_block_temperature(4)
            thermocycler.open_lid()
        if DIAGNOSTIC == True:
            print('Thermocycler held 32 for '+str(FRAGTIME)+' min')
        # =========== End section ================================
########################################################################################################################
 
########################################################################################################################
    #Section 2 -- Ligation
    if STEP_LIG == True:
        protocol.comment('==============================================')
        protocol.comment('--> Adapter Ligation')
        protocol.comment('==============================================')
        protocol.comment('')
        protocol.comment('--> Adding Barcodes')
        protocol.comment('')
        if DIAGNOSTIC == True:
            print('Adding Ligation Barcodes')
        # Section 2.1 -- Adding barcodes
        #========== Steps 1 - 7 ==============================
        for x in range(COLUMNS):
            Target_column = 'A' + str(x+1)
            Source_column = 'A'+ str(x+7)
            tips = 'A' + str(x+7)    
            print(tips+' from tiprack_50_1')
            p50.pick_up_tip(tiprack_50_1.wells_by_name()[tips])
            add_barcodes(5, 3, 10, reagent_plate_1, Source_column, sample_plate_1, Target_column)
            p50.drop_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p50_1')
            print('There are '+ str(12-(COLUMNS))+' left in p50_1')
        #==== Move tiprack_50_2 ==============================
        move_labware(tiprack_50_1, TRASH,'nah')
        move_labware(tiprack_50_2, 'B2','nah')
        #============ End Section ============================              
        # Section 2.2 -- Adding Ligation Mix
        protocol.comment('')
        protocol.comment('--> Adding Lig')
        protocol.comment('')
        if DIAGNOSTIC == True:
            print('Adding Ligation enzyme mix')
        #================ Steps 1 - 8 ==========================
        for x in range(COLUMNS):
            if x < 3:
                source_well = 'A2'
            else:
                source_well = 'A3'
            Target_column = 'A' + str(x+1)
            tips = 'A' + str(x+1)
            if x < 3:
                offset = 2.5 - x
            else: 
                offset = 2.5 - (x-3)
            print(tips+' from tiprack_50_2')
            print('offset = '+ str(offset))
            p50.pick_up_tip(tiprack_50_2.wells_by_name()[tips])
            add_ligation_mix(Ligvol, 5, Ligmixvol, reagent_plate_1,source_well, sample_plate_1, Target_column, offset)
            p50.drop_tip()
        if DIAGNOSTIC == True:
            print('Used'+str(COLUMNS+COLUMNS+COLUMNS)+' columns of tips from p50_1')
            print('There are '+ str(12-(COLUMNS+COLUMNS))+' left in p50_1')   
        #============= End Section =========================
        # ============== Step 9 ========================
        if DRYRUN == False:
            #thermocycler.close_lid()
            profile_LIG = [
                {'temperature': 20, 'hold_time_minutes': 15}
                ]
            thermocycler.execute_profile(steps=profile_LIG, repetitions=1, block_max_volume=50)
            thermocycler.set_block_temperature(10)
        #thermocycler.open_lid()
        if DIAGNOSTIC == True:
            print('Thermocycler held DID LIGATION :)')
        # ============== End Section ====================
        
        # Section 2.3 -- Add Water
        # ========== Steps 1-3 ===============
        if REACTIONPERCENT != 100:
            protocol.comment('--> Adding Water')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()['A11'])
            for x in range(COLUMNS):
                Target_column = 'A' + str(x+1)
                add_water(50, Water, sample_plate_1, Target_column)
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_r')
            print('Returned tips') 
         # ========== End section =============
###############################################################################################

###############################################################################################    
    # Section 3 - Bead Cleanup 1 (0.75x ratio of beads to sample)
    if STEP_CLEANUP_1 == True:
        protocol.comment('==============================================')
        protocol.comment('--> Cleanup 1')
        protocol.comment('==============================================')
        protocol.comment('')
        protocol.comment('--> ADDING CleanupBead (0.75x)')
        protocol.comment('')
        
        # Section 3.1 Add Cleanup Beads and Samples
        if DIAGNOSTIC == True:
            print('Adding cleanup Beads') 
        #========= Steps 1 - 13 =========================
        for x in range(COLUMNS):
            Target_column = 'A' + str(x+1)
            print(Target_column+' from tiprack_200_R')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Target_column])
            add_beads(75, 6, CleanupBead, CleanupPlate_1, Target_column)
            add_sample(100, sample_plate_1, CleanupPlate_1, Target_column, Target_column)
            bead_mixing(CleanupPlate_1, Target_column)
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_r')
            print('Returned tips') 
        #========= Steps 14 - 16 =======================
        heatershaker.set_and_wait_for_shake_speed(rpm=1600)
        protocol.delay(5*60 if DRYRUN == False else 0.1*60)
        heatershaker.deactivate_shaker()
        if DIAGNOSTIC == True:
            print('Shake for 5 min')
        #===============================================
        # GRIPPER MOVE (CleanupPlate_1)  HEATER SHAKER --> MAG BLOCK
        move_labware(CleanupPlate_1,mag_block,'ye')
        if DRYRUN == False:
            protocol.delay(minutes=4)
        if DIAGNOSTIC == True:
            print('Move CleanupPlate_1 from HS to Mag Block') 
        #========= End Section =========================
        
        # Section 3.2 Remove Supernatant
        protocol.comment('')
        protocol.comment('--> Cleanup 1 -- Removing Supernatant')
        protocol.comment('')
        print('Removing supernatant')
        #=========== Steps 1 - 5 ================
        for x in range(COLUMNS):
            Target_column = 'A' + str(x+1)
            print(Target_column+' from tiprack_200_R') 
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Target_column])
            remove_supernatant(p1000,6, 200, 200, CleanupPlate_1, Target_column)
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_r')
            print('Returned tips') 
        #============= End Section ===============
        
        # Section 3.3 -- Ethanol Wash
        for X in range(2):
            protocol.comment('')
            protocol.comment('--> Cleanup 1 -- ETOH Wash '+str(x+1))
            protocol.comment('')
            print('Ethanol wash '+str(X+1))
            #============ Steps 1 - 7 ======================
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()['A12'])
            for x in range(COLUMNS):
                if x < 2:
                    source_well = 'A4'
                if  x == 2 or x == 3:
                    source_well = 'A5'
                if  x >= 4:
                    source_well = 'A6'
                Target_column = 'A' + str(x+1)
                print(Target_column+' from tiprack_200_R')
                print('Pulling from '+source_well+' on reservoir plate')
                ethanol_wash(150, reservoir,source_well, CleanupPlate_1, Target_column)
            p1000.return_tip()
            if DIAGNOSTIC == True:
                print('Used A1 column of tips from p200_1')
                print('Returned tips')
            if DRYRUN == False:
                protocol.delay(seconds=30)
         #============== End Section ======================
            
            # Section 3.4 -- Remove Ethanol Wash
            protocol.comment('')
            protocol.comment('--> Clean up 1 -- Remove ETOH Wash '+str(x+1))
            protocol.comment('')
            print('Removing Ethanol wash '+str(X))
            #============= Steps 1 - 9 =======================
            for x in range(COLUMNS):
                Target_column = 'A' + str(x+1)
                print(Target_column+' from tiprack_200_R')
                p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Target_column])
                remove_ethanol(200, CleanupPlate_1, Target_column)
                p1000.return_tip()
            if DRYRUN == False:
                protocol.delay(minutes=1)
            if DIAGNOSTIC == True:
                print('Used '+str(COLUMNS)+' columns of tips from p200_R')
                print('Returned tips')
        # =============== End Section =========================
        
        # Section 3.5 -- Remove residual Wash
        
        # ============== Steps 1 - 5 ===========================
        protocol.comment('')
        protocol.comment('--> Removing Residual Wash')
        protocol.comment('')
        print('Removing residual wash')
        #===============================================
        for x in range(COLUMNS):
            Target_column = 'A' + str(x+1)
            print(Target_column+' from tiprack_200_R')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Target_column])
            p1000.move_to(CleanupPlate_1[Target_column].bottom(z=Deepwell_MagBlock_Z_offset))
            p1000.aspirate(200)
            #======L Waste Volume Check======
            waste_volume_check(200)
            #================================ 
            p1000.dispense(200, Liquid_trash.top(z=0))
            protocol.delay(seconds=1)
            p1000.blow_out()
            p1000.return_tip()
        if DRYRUN == False:
            protocol.delay(minutes=0.5)
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_R')
            print('Returned tips')
        #================ Step 6 =============================
        # GRIPPER MOVE (CleanupPlate_1) FROM MAG BLOCK --> HEATERSHAKER
        move_labware(CleanupPlate_1,heatershaker,'ye')
        if DIAGNOSTIC == True:
            print('Moved Cleanup from Mag to HS')
        #=================== End Section =============================

        # Section 3.6 -- Add Resuspension Buffer
        protocol.comment('--> Adding RSB')
        print('Adding RSB')
        #============== Steps 1 - 7 ==========================
        for x in range(COLUMNS):
            Target_column = 'A' + str(x+1)
            print(Target_column+' from tiprack_50_R')
            p50.pick_up_tip(tiprack_50_R.wells_by_name()[Target_column])
            add_resuspension_buffer(Resusup_1+2, RSB, CleanupPlate_1, Target_column)
            p50.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p50_R')
            print('Returned tips')
        #================ Step 8 ====================
        heatershaker.set_and_wait_for_shake_speed(rpm=2000)
        protocol.delay(5*60 if DRYRUN == False else 0.1*60)
        heatershaker.deactivate_shaker()
        if DIAGNOSTIC == True:
            print('Shake for 5 min')
        #================= Step 9 ====================================================================
        # GRIPPER MOVE (CleanupPlate_1) FROM HEATERSHAKER --> MAG BLOCK
        move_labware(CleanupPlate_1,mag_block,'ye')
        thermocycler.set_lid_temperature(105)
        if DRYRUN == False:
            protocol.delay(minutes=0.5)
        if DIAGNOSTIC == True:
            print('Move Cleanup from HS to Mag Block')
        #=============== End Section ==================================================================
###############################################################################################

##############################################################################################        
    # Section 4 -- Library Amplification                   
    if STEP_PCR == True:
        protocol.comment('==============================================')
        protocol.comment('--> Amplification')
        protocol.comment('==============================================')
        protocol.comment('')
        protocol.comment('--> Adding Primer and sample')
        protocol.comment('')
        print("Adding primer and sample")
        # Section 4.1 -- Add Primers and transfer samples        
        #=========  Steps 1 - 9 ==============================
        for x in range(COLUMNS):           
            Source_column = 'A' + str(x+1)
            k = x+1 + add            
            Target_column = 'A' + str(k+1)
            tips = 'A' + str(k+1)
            print(tips+' from tiprack_50_2')
            p50.pick_up_tip(tiprack_50_2.wells_by_name()[tips])
            transfer_supernatant(Resusup_1,CleanupPlate_1,Source_column,sample_plate_1,Target_column,'yes')
            p50.drop_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS+COLUMNS+COLUMNS+COLUMNS)+' columns of tips from p50_1')
            print('Trashed tips')
        #=========== End Section =====================
        move_labware(CleanupPlate_1, heatershaker,'ye')
        if DIAGNOSTIC == True:
            print('Move CleanupPlate_1 from Mag Block to HS')        
        # Section 4.2 -- Add PCR Master Mix
        protocol.comment('--> Adding PCR')
        print('Adding PCR Master mix')
        #========= Steps 1 - 8 ==========================
        for x in range(COLUMNS):
            k = x+2+add 
            Target_column = 'A' + str(k)
            tips = 'A' + str(x+1)
            print(tips+' from tiprack_50_3')
            p50.pick_up_tip(tiprack_50_3.wells_by_name()[tips])
            add_PCR_mix(PCRmixvol,PCRrx/2,2,10,sample_plate_1,Target_column)
            p50.drop_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS+COLUMNS+COLUMNS+COLUMNS+COLUMNS)+' columns of tips from p50_1')
            print('Trashed tips')
        #========== End Section ========================
        # Section 4.3 PCR Run     
        # ========== Steps 1-3 =========================
        thermocycler.close_lid()
        if DRYRUN == False:
            profile_PCR_1 = [
                {'temperature': 98, 'hold_time_seconds': 120}
                ]
            thermocycler.execute_profile(steps=profile_PCR_1, repetitions=1, block_max_volume=50)
            profile_PCR_2 = [
                {'temperature': 98, 'hold_time_seconds': 20},
                {'temperature': 60, 'hold_time_seconds': 30},
                {'temperature': 72, 'hold_time_seconds': 30}
                ]
            thermocycler.execute_profile(steps=profile_PCR_2, repetitions=PCRCYCLES, block_max_volume=50)
            profile_PCR_3 = [
                {'temperature': 72, 'hold_time_minutes': 1}
                ]
            thermocycler.execute_profile(steps=profile_PCR_3, repetitions=1, block_max_volume=50)
            thermocycler.set_block_temperature(4)
        if DIAGNOSTIC == True:
            print('Did amp :p')
        thermocycler.open_lid()
        # ============ End Section ======================       
        # Section 4.4 -- Add Water
        print("Addbug water")
        if REACTIONPERCENT != 100:
            protocol.comment('--> Adding Water')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()['A11'])
            for x in range(COLUMNS):
                k = x+1 + add 
                Target_column = 'A' + str(k)
                add_water(25,Water,sample_plate_1,Target_column)
            p1000.return_tip()
            if DIAGNOSTIC == True:
                print('Used A2 column of tips from p200_1')
                print('Returned tips')
        # ======== End Section ====================
###############################################################################################        

###############################################################################################        
    # Section 5 -- Bead Cleanup 2
    if STEP_CLEANUP_3 == True:
        protocol.comment('==============================================')
        protocol.comment('--> Cleanup 3')
        protocol.comment('==============================================')
        
        print('========= CLEANUP 3 ==========')
        CleanupPlate_2 = CleanupPlate_1
        #============================================================================================
        if DIAGNOSTIC == True:
            print('Move CleanupPlate_2 from Mag Block to HS')
        # Section 5.1 -- Add Cleanup Beads and samples
        protocol.comment('--> ADDING CleanupBead (1.2x)') 
        print('Adding Beads')
        #============ Steps 1 - 13 ========================
        for x in range(COLUMNS):
            print(x)
            Source_column = 'A' + str(x+1)
            k = x + add + 2     
            Target_column = 'A' + str(k)
            print(Target_column+' from tiprack_200_R')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Source_column])
            add_beads(50,6,CleanupBead,CleanupPlate_2,Target_column)
            add_sample(50,sample_plate_1,CleanupPlate_2,Target_column,Target_column)
            bead_mixing(CleanupPlate_2,Target_column)
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_R')
            print('Returned tips')
        #=============== End Section =====================        
        # =============== Step 14 ====================
        heatershaker.set_and_wait_for_shake_speed(rpm=1600)
        protocol.delay(5*60 if DRYRUN == False else 0.1*60)
        heatershaker.deactivate_shaker()
        if DIAGNOSTIC == True:
            print('Shake for 5 min')
        #================ Step 15 ===================================================================
        # GRIPPER MOVE (CleanupPlate_2) HEATER SHAKER --> MAG BLOCK
        heatershaker.open_labware_latch()
        protocol.move_labware(labware=CleanupPlate_2,new_location=mag_block,use_gripper=USE_GRIPPER)
        heatershaker.close_labware_latch()
        if DIAGNOSTIC == True:
            print('Moved current cleanup plate from HS to Mag Block')
        #================ Step 16 ===================================================================
        if DRYRUN == False:
            protocol.delay(minutes=4)
        #================ End Section =====================
        # Section 5.2 -- Remove Supernatant
        # =============== Steps 1 - 5 ===================== 
        protocol.comment('')
        protocol.comment('--> Clean up 2 -- Removing Supernatant')
        protocol.comment('')
        print('Remove Supe')
        for x in range(COLUMNS):
            Source_column = 'A' + str(x+1)
            k = x+2 + add            
            Target_column = 'A' + str(k)
            print(Target_column+' from tiprack_200_R')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Source_column])
            remove_supernatant(p1000,3,200,200,CleanupPlate_2,Target_column)
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_R')
            print('Returned tips')
        #===============================================
        # Section 5.3 -- Ethanol Wash
        # ============== Steps 1 - 7 ===================
        protocol.comment('')
        protocol.comment('--> Cleanup 2 -- ETOH Wash')
        protocol.comment('')
        print('Adding ETOH')
        for X in range(2):
            #===============================================
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()['A12'])
            for x in range(COLUMNS):
                if x < 2:
                    source_well = 'A4'
                if  x == 2 or x == 3:
                    source_well = 'A5'
                if  x >= 4:
                    source_well = 'A6'
                k = x+2 + add           
                Target_column = 'A' + str(k)
                print(Target_column+' from tiprack_200_R')
                print('Pulling from '+source_well+' on reservoir plate')
                ethanol_wash(150,reservoir,'A4',CleanupPlate_2,Target_column)
            p1000.return_tip()
            if DIAGNOSTIC == True:
                print('Used A1 columns of tips from p200_1')
                print('Returned tips')
            if DRYRUN == False:
                protocol.delay(seconds=30)
                #===============================================
            # ========= Section 5.4 -- Remove ethanol Wash
            protocol.comment('')
            protocol.comment('--> Remove ETOH Wash '+str(x+1))
            protocol.comment('')
            print('Remove ETOH')
            #============== Steps 1 - 9 ====================
            for x in range(COLUMNS):
                Source_column = 'A' + str(x+1)
                k = x+2 + add         
                Target_column = 'A' + str(k)
                print(Target_column+' from tiprack_200_R')
                p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Source_column])
                remove_ethanol(200,CleanupPlate_2,Target_column)
                p1000.return_tip() 
            if DRYRUN == False:
                protocol.delay(minutes=1) 
            if DIAGNOSTIC == True:
                print('Used '+str(COLUMNS)+' columns of tips from p200_R')
                print('Returned tips')                
        #=================== End Section ==================      
        # ============ Section 5.5 -- Remove residual wash
        protocol.comment('')
        protocol.comment('--> Cleanup 2 -- Removing Residual Wash')
        protocol.comment('')
        print('Remove Residual wash')
        #================ Steps 1 - 4 ===================
        for x in range(COLUMNS):
            Source_column = 'A' + str(x+1)
            k = x+2 + add           
            Target_column = 'A' + str(k)
            print(Target_column+' from tiprack_200_R')
            p1000.pick_up_tip(tiprack_200_R.wells_by_name()[Source_column])
            p1000.move_to(CleanupPlate_2[Target_column].bottom(Deepwell_MagBlock_Z_offset))
            p1000.aspirate(50)
            #======L Waste Volume Check======
            waste_volume_check(50)
            #================================ 
            p1000.dispense(50, Liquid_trash.top(z=0))
            protocol.delay(seconds=1)
            p1000.blow_out()
            p1000.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p200_R')
            print('Returned tips')            
        #================= Step 5 =================
        if DRYRUN == False:
            protocol.delay(minutes=0.5)
        #================= Step 6 ==================
        # GRIPPER MOVE (CleanupPlate_2) FROM MAG BLOCK --> HEATERSHAKER
        heatershaker.open_labware_latch()
        protocol.move_labware(labware=CleanupPlate_2,new_location=heatershaker, use_gripper=USE_GRIPPER)
        heatershaker.close_labware_latch()
        if DIAGNOSTIC == True:
            print('Move Current cleanup plate from Mag Block to HS')
        #================== End Section ============
        # ========== Section 5.6 -- Add Resuspension Buffer
        protocol.comment('')
        protocol.comment('--> Final elution -- Adding RSB')
        protocol.comment('')
        print('Adding RSB')
        #================ Steps 1-7 ===============
        for x in range(COLUMNS):
            Source_column = 'A' + str(x+1)
            k = x+2 + add           
            Target_column = 'A' + str(k)
            print(Target_column+' from tiprack_50_R')
            p50.pick_up_tip(tiprack_50_R.wells_by_name()[Source_column])
            add_resuspension_buffer(FELUTION+2,RSB,CleanupPlate_2,Target_column)
            p50.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p50_R')
            print('Returned tips')
        #================ Step 8 ====================
        heatershaker.set_and_wait_for_shake_speed(rpm=2000)
        protocol.delay(5*60 if DRYRUN == False else 0.1*60)
        heatershaker.deactivate_shaker()
        if DIAGNOSTIC == True:
            print('Shake for 5 min')
        #================ Step 9 =====================
        # GRIPPER MOVE (CleanupPlate_2) FROM HEATERSHAKER --> MAG BLOCK
        heatershaker.open_labware_latch()
        protocol.move_labware(labware=CleanupPlate_2,new_location=mag_block,use_gripper=USE_GRIPPER)
        heatershaker.close_labware_latch()
        if DIAGNOSTIC == True:
            print('Move Cleanup Plate from HS to Mag Block')
        #=============================================
        if DRYRUN == False:
            protocol.delay(minutes=3)
        #== End Section ================================
        # ==== Section 5.7 -- Transfer Supernatant
        protocol.comment('')
        protocol.comment('--> Transferring Supernatant')
        protocol.comment('')
        #========= Steps 1 - 6 ==========================
        heatershaker.open_labware_latch()
        protocol.move_labware(labware=sample_plate_2, new_location=heatershaker, use_gripper=USE_GRIPPER)
        heatershaker.close_labware_latch()
        destination = sample_plate_2
        for x in range(COLUMNS):
            print("Cleanup 3 transfer")
            Source_column = 'A' + str(x+7)
            tips = 'A' + str(x+7)
            Target_column = 'A' + str(x+7)
            print(Target_column+' from tiprack_50_R')
            p50.pick_up_tip(tiprack_50_R.wells_by_name()[tips])
            transfer_supernatant(FELUTION,CleanupPlate_2,Target_column,sample_plate_2,Target_column,'no')
            p50.return_tip()
        if DIAGNOSTIC == True:
            print('Used '+str(COLUMNS)+' columns of tips from p50_R')
            print('Returned tips')
        #=========== End Section =========================        
    # =================================================================================================
    # ========================================== PROTOCOL END =========================================
    # =================================================================================================
    if DEACTIVATE_TEMP == True:
        thermocycler.deactivate_block()
        thermocycler.deactivate_lid()
        temp_block.deactivate()
    heatershaker.open_labware_latch()
import numpy as np
import cv2
import random
import math
import copy
from collections import defaultdict
import os
import imageio
from algos.wfc_lib.wfc_utils import (
    hash_function,
    is_same_pattern,
    img_equal,
    cv_write,
    cv_img,
    cv_wait,
    get_hash_to_code,
    prepare_write_outputs,
)
from algos.wfc_lib.wfc_encode import get_encoded_patterns
from algos.wfc_lib.wfc_adjacency import extract_adjacency, build_adjacency_matrix
from algos.wfc_lib.wfc_output import (
    build_output_matrix,
    observe,
    propagate,
    render,
    pad_ground,
)
from algos.wfc_lib.wfc_backtrack import (
    backtrack_memory,
    update_queue,
    prepare_backtrack
)

"""
Sample over NxN crops of Input image, to create selection array
for output, each grid selects out of random one of the selection array membe
"""


def wfc_overlap_run(
    input_img,
    N=3,
    output_size=32,
    output_name="out_video.avi",
    GROUND=False,
    WRITE=False,
    VISUALIZE_ENCODE=False,
    VISUALIZE_ADJACENCY=False,
    MAX_BACKTRACK = 5,
    WRITE_VIDEO=False,
    SPECS={},
):
    ###################################################
    print("RUNNING")
    video_out = []
    ###################################################
    print("ENCODING...")
    pattern_set, hash_frequency_dict, ground = get_encoded_patterns(
        input_img,
        N,
        VISUALIZE=VISUALIZE_ENCODE,
        GROUND=GROUND,
        WRITE=WRITE,
        SPECS=SPECS,
    )
    (
        pattern_code_set,
        hash_to_code_dict,
        avg_color_set,
        ground,
        code_frequencies,
    ) = get_hash_to_code(pattern_set, ground, hash_frequency_dict, GROUND=GROUND)
    ###################################################
    print("EXTRACTING ADJACENCY...")
    adjacency_list = extract_adjacency(
        hash_to_code_dict, pattern_set, N, VISUALIZE=VISUALIZE_ADJACENCY
    )
    adjacency_matrices = build_adjacency_matrix(
        adjacency_list, pattern_code_set, WRITE=WRITE
    )
    ###################################################
    print("BUILDING OUTPUT MATRIX...")
    output_matrix = build_output_matrix(code_frequencies, output_size)
    output_matrix = (
        pad_ground(output_matrix, ground,pattern_code_set,code_frequencies) if GROUND else output_matrix
    )
    ###################################################
    print("PROPAGATING...")
    output_matrix = propagate(
        output_matrix, avg_color_set, adjacency_matrices, code_frequencies
    )        
    backtrack_queue,output_matrix,backtrack_no = prepare_backtrack(copy.deepcopy(output_matrix),MAX_BACKTRACK)
    t = 0
    while True:
        #===========================
        # OBSERVE
        #===========================
        done,contradiction, output_matrix = observe(
            output_matrix, pattern_code_set, hash_frequency_dict, code_frequencies
        )
        t +=1
        if(t%3==0):
            contradiction = True
        #===========================
        # BACKTRACK IF CONTRADICTION
        #===========================
        if(contradiction):
            print("Contradiction! Backtracking...step {}".format(backtrack_no))
            try:
                output_matrix = copy.deepcopy(backtrack_memory(backtrack_queue,backtrack_no))
                backtrack_no = min(backtrack_no+1,MAX_BACKTRACK)
            except AssertionError:
                print("no previous state to backtrack on")                
                backtrack_no = 1
        else:            
            backtrack_queue = update_queue(backtrack_queue, copy.deepcopy(output_matrix))
            backtrack_no = max(1,backtrack_no-1)
        #===========================
        # PROPAGATE
        #===========================
        output_matrix = propagate(
            output_matrix, avg_color_set, adjacency_matrices, code_frequencies
        )
        #===========================
        # RENDER
        #===========================
        rendered = render(
            output_matrix, output_size, N, pattern_code_set, WRITE_VIDEO=WRITE_VIDEO
        )
        #===========================
        # DISPLAY AND WRITE(OPTIONAL)
        #===========================
        if WRITE_VIDEO:
            video_out.append(rendered.astype(np.uint8))
        k = cv2.waitKey(1)
        if k == ord("q"):
            break
        # if done: exit()
    cv2.destroyAllWindows()
    if WRITE_VIDEO:
        imageio.mimsave(os.path.join("wfc_outputs", output_name + ".gif"), video_out)

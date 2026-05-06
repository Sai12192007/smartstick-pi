def get_direction(box, frame_width):
    """
    Determines direction based on the center of the bounding box.
    box: (startX, startY, endX, endY)
    frame_width: width of the frame
    """
    if box is None:
        return "none"
    
    startX, startY, endX, endY = box
    center_x = (startX + endX) / 2
    
    # Divide frame into 3 sectors
    left_boundary = frame_width / 3
    right_boundary = (frame_width / 3) * 2
    
    if center_x < left_boundary:
        return "left"
    elif center_x > right_boundary:
        return "right"
    else:
        return "center"

def format_data(obj_name, distance, direction):
    """
    Formats data for socket transmission.
    Example: person,45,left\n
    """
    return f"{obj_name},{int(distance)},{direction}\n"

import sys
import getopt

import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False, sackMode=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        if sackMode:
            raise NotImplementedError #remove this line when you implement SACK
        self.sending_window = []
        self.window_start_number = 0
        self.end_reached = False #end of data stream
        self.should_stop = False
        self.duplicate_count = 0
        self.next_msg = None
        self.cur_msg = None

        self.end_ack_received = False
        self.end_seq_no = -1

    # Main sending loop.

    def start(self):
        """
        while not self.end_ack_received:
            self.send__fill_the_window()
            response = self.receive(0.5)
            if response and Checksum.validate_checksum(response):
                response_type, ack_num_str, data, checksum = self.split_packet(response)
                ack_num = int(ack_num_str)
                self.check_for_stop(ack_num)
                if ack_num - self.window_start_number > 0:
                    self.handle_new_ack(ack_num)
                else:
                    self.handle_dup_ack(ack_num)
            else:
                self.handle_timeout()
        """
        while not self.end_ack_received:
            self.send__fill_the_window()
            response = self.receive(0.5)
            if response is None:
                self.handle_timeout()
            else:
                if not Checksum.validate_checksum(response):
                    self.handle_timeout()
                    continue
                response_type, ack_num_str, _, checksum = self.split_packet(response)
                if response_type != "ack": continue
                ack_num = int(ack_num_str)
                if ack_num > self.window_start_number and ack_num <= self.window_start_number + len(self.sending_window):
                    self.handle_new_ack(ack_num)
                elif ack_num == self.window_start_number: #dupack
                    self.handle_dup_ack(ack_num)

        self.infile.close()

    def send__fill_the_window(self):
        """
        allowance = 5 - len(self.sending_window)
        for i in range(0, allowance):
            self.read_stream()

            msg = self.cur_msg
            seq_no = self.window_start_number + len(self.sending_window) + i
            msg_type = self.get_msg_type(seq_no)

            if msg_type == "end":
                self.end_seq_no = int(seq_no)

            packet = self.make_packet(msg_type, seq_no, msg)
            self.send(packet)
            self.sending_window.append(packet)

            self.cur_msg = self.next_msg

            if msg_type == "end": #can refactor this
                break

        """
        #can check at main loop, use if to determine if we should send_fill or not
        if self.end_seq_no is not -1:
            return

        used_window = len(self.sending_window)
        free_space = 5 - used_window
        for i in range(free_space):

            if i == 0:
                msg = self.infile.read(1372)
                self.read_stream(1372)

                seqno = self.window_start_number + used_window + i
                msg_type = self.get_msg_type(seqno)
                if msg_type == "end":
                    self.end_seq_no = int(seqno)
                packet = self.make_packet(msg_type, seqno, msg)
                self.send(packet)
                self.sending_window.append(packet)
            else:

                self.cur_msg = self.next_msg
                self.read_stream(1372)

                msg = self.cur_msg
                seqno = self.window_start_number + used_window + i
                msg_type = self.get_msg_type(seqno)
                if msg_type == "end":
                    self.end_seq_no = int(seqno)
                packet = self.make_packet(msg_type, seqno, msg)
                self.send(packet)
                self.sending_window.append(packet)

            if msg_type == "end":
                break

    def read_stream(self, buffer_size): #peek the next data stream chunk, if next_msg is empty, that means it's the end

        #if self.end_reached:
        #    self.cur_msg = ""
        #    return

        #self.cur_msg = self.infile.read(1372)
        self.next_msg = self.infile.read(1372)
        if self.next_msg == "": self.end_reached = True
        """
        if self.end_reached: return ""
        if self.next_msg is None:
            self.next_msg = self.infile.read(buffer_size)
            if self.next_msg == "": return ""
        msg = self.next_msg
        self.next_msg = self.infile.read(buffer_size)
        if self.next_msg == "": self.end_reached = True
        return msg
        """

    def get_msg_type(self, seq_no):
        if seq_no == 0: return 'start'
        if self.end_reached: return 'end'
        return 'data'

    def check_for_stop(self, ack):
        if ack - self.window_start_number == 1: #means received "end" ack
            self.should_stop = True

    def handle_timeout(self):
        for p in self.sending_window:
            self.send(p)

    def handle_new_ack(self, ack):
        if (self.end_seq_no + 1 == ack):
            self.end_ack_received = True

        items_to_remove = ack - self.window_start_number
        for i in range(0, items_to_remove):
            self.sending_window.pop(0)
        self.window_start_number = ack

    def handle_dup_ack(self, ack):
        self.duplicate_count += 1
        if self.duplicate_count == 3:
            self.send(self.sending_window[0])
            #self.duplicate_count = 0 #resets the counter

    def log(self, msg):
        if self.debug:
            print msg


'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"
        print "-k | --sack Enable selective acknowledgement mode"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:dk", ["file=", "port=", "address=", "debug=", "sack="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False
    sackMode = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True
        elif o in ("-k", "--sack="):
            sackMode = True

    s = Sender(dest, port, filename, debug, sackMode)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()

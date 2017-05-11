--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.2
-- Dumped by pg_dump version 9.6.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgres; Type: COMMENT; Schema: -; Owner: Norman
--

COMMENT ON DATABASE postgres IS 'default administrative connection database';


--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: answer; Type: TABLE; Schema: public; Owner: Norman
--

CREATE TABLE answer (
    token text,
    value text
);


ALTER TABLE answer OWNER TO "Norman";

--
-- Name: error_list; Type: TABLE; Schema: public; Owner: heqingy
--

CREATE TABLE error_list (
    token text,
    path text,
    message text
);


ALTER TABLE error_list OWNER TO heqingy;

--
-- Name: standard; Type: TABLE; Schema: public; Owner: Norman
--

CREATE TABLE standard (
    token text,
    value text
);


ALTER TABLE standard OWNER TO "Norman";

--
-- Name: status; Type: TABLE; Schema: public; Owner: Norman
--

CREATE TABLE status (
    token text,
    processed integer,
    total integer
);


ALTER TABLE status OWNER TO "Norman";

--
-- Data for Name: answer; Type: TABLE DATA; Schema: public; Owner: Norman
--

COPY answer (token, value) FROM stdin;
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/student/student_20170510235421q9AN5yQ2rd-00001.jpg", "result": {"answer": ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "AB", "BC", "CD", "DE", "ABCDE"], "name_image": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/name/2017_05_10_23_54_30_48SJw.png", "id": "007"}}
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/student/student_20170510235421q9AN5yQ2rd-00002.jpg", "result": {"answer": ["A", "B", "C", "D", "E", "E", "D", "C", "B", "A", "A", "B", "C", "D", "E", "E", "D", "C", "B", "A", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E"], "name_image": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/name/2017_05_10_23_54_31_DevTp.png", "id": "987654567890"}}
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/student/student_20170510235421q9AN5yQ2rd-00003.jpg", "result": {"answer": ["AB", "BC", "CD", "DE", "ABCDE", "AB", "BC", "CD", "DE", "BCD", "A", "B", "C", "D", "E", "B", "C", "D", "E", "A", "C", "D", "E", "ABC", "CDE", "A", "A", "A", "A", "A", "ABC", "BCD", "CDE", "ABCD", "ABCDE"], "name_image": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/name/2017_05_10_23_54_32_reC5t.png", "id": "012345432101"}}
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/student/student_20170510235421q9AN5yQ2rd-00004.jpg", "result": {"answer": ["B", "C", "D", "E", "A", "C", "D", "E", "A", "B", "D", "E", "A", "B", "C", "E", "A", "B", "C", "D", "A", "B", "C", "D", "E", "B", "C", "D", "C", "B", "AB", "AC", "AD", "AE", "ABCDE"], "name_image": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/name/2017_05_10_23_54_33_Vlq0S.png", "id": "0123456789"}}
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/student/student_20170510235421q9AN5yQ2rd-00005.jpg", "result": {"answer": ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E"], "name_image": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/name/2017_05_10_23_54_34_jHm5W.png", "id": "9876543210"}}
\.


--
-- Data for Name: error_list; Type: TABLE DATA; Schema: public; Owner: heqingy
--

COPY error_list (token, path, message) FROM stdin;
\.


--
-- Data for Name: standard; Type: TABLE DATA; Schema: public; Owner: Norman
--

COPY standard (token, value) FROM stdin;
201705102354063YhS4GwAhi	{"status": "success", "path": "/Users/Norman/git/Answer-Sheet-OCR/simple_web/file_storage/201705102354063YhS4GwAhi/teacher/standard-00001.jpg", "result": {"answer": ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "A", "B", "C", "D", "E", "AB", "BC", "CD", "DE", "ABCDE"], "name_image": "/tmp/2017_05_10_23_54_30_iWfab.png", "id": ""}}
\.


--
-- Data for Name: status; Type: TABLE DATA; Schema: public; Owner: Norman
--

COPY status (token, processed, total) FROM stdin;
201705102354063YhS4GwAhi	5	5
\.


--
-- Name: answer; Type: ACL; Schema: public; Owner: Norman
--

GRANT ALL ON TABLE answer TO heqing;
GRANT ALL ON TABLE answer TO heqingy;


--
-- Name: standard; Type: ACL; Schema: public; Owner: Norman
--

GRANT ALL ON TABLE standard TO heqing;
GRANT ALL ON TABLE standard TO heqingy;


--
-- Name: status; Type: ACL; Schema: public; Owner: Norman
--

GRANT ALL ON TABLE status TO heqing;
GRANT ALL ON TABLE status TO heqingy;


--
-- PostgreSQL database dump complete
--


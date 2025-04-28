--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admin_activity_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admin_activity_logs (
    id integer NOT NULL,
    admin_id integer,
    action character varying,
    details character varying,
    "timestamp" timestamp without time zone
);


ALTER TABLE public.admin_activity_logs OWNER TO postgres;

--
-- Name: admin_activity_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admin_activity_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_activity_logs_id_seq OWNER TO postgres;

--
-- Name: admin_activity_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admin_activity_logs_id_seq OWNED BY public.admin_activity_logs.id;


--
-- Name: admin_stations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admin_stations (
    admin_id integer,
    station_id integer
);


ALTER TABLE public.admin_stations OWNER TO postgres;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admins (
    id integer NOT NULL,
    username character varying,
    email character varying,
    hashed_password character varying,
    is_super_admin boolean,
    is_active boolean,
    created_at timestamp without time zone,
    last_login timestamp without time zone
);


ALTER TABLE public.admins OWNER TO postgres;

--
-- Name: admins_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admins_id_seq OWNER TO postgres;

--
-- Name: admins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admins_id_seq OWNED BY public.admins.id;


--
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bookings (
    id integer NOT NULL,
    user_id integer,
    station_id integer,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    total_cost double precision NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    notes text
);


ALTER TABLE public.bookings OWNER TO postgres;

--
-- Name: bookings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bookings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bookings_id_seq OWNER TO postgres;

--
-- Name: bookings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bookings_id_seq OWNED BY public.bookings.id;


--
-- Name: charging_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.charging_configs (
    id integer NOT NULL,
    station_id integer,
    charging_type character varying,
    connector_type character varying,
    power_output double precision,
    cost_per_kwh double precision
);


ALTER TABLE public.charging_configs OWNER TO postgres;

--
-- Name: charging_configs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.charging_configs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.charging_configs_id_seq OWNER TO postgres;

--
-- Name: charging_configs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.charging_configs_id_seq OWNED BY public.charging_configs.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payments (
    id integer NOT NULL,
    user_id integer NOT NULL,
    booking_id integer,
    order_id character varying(255) NOT NULL,
    amount double precision NOT NULL,
    currency character varying(3) DEFAULT 'USD'::character varying,
    status character varying(20) DEFAULT 'created'::character varying,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    payment_method character varying(50) DEFAULT 'paypal'::character varying,
    transaction_id character varying(255)
);


ALTER TABLE public.payments OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payments_id_seq OWNER TO postgres;

--
-- Name: payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payments_id_seq OWNED BY public.payments.id;


--
-- Name: stations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stations (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    is_available boolean DEFAULT true,
    is_maintenance boolean DEFAULT false,
    location text
);


ALTER TABLE public.stations OWNER TO postgres;

--
-- Name: stations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stations_id_seq OWNER TO postgres;

--
-- Name: stations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stations_id_seq OWNED BY public.stations.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    hashed_password character varying(100) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    phone_number character varying,
    is_active boolean
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: admin_activity_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_activity_logs ALTER COLUMN id SET DEFAULT nextval('public.admin_activity_logs_id_seq'::regclass);


--
-- Name: admins id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins ALTER COLUMN id SET DEFAULT nextval('public.admins_id_seq'::regclass);


--
-- Name: bookings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings ALTER COLUMN id SET DEFAULT nextval('public.bookings_id_seq'::regclass);


--
-- Name: charging_configs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charging_configs ALTER COLUMN id SET DEFAULT nextval('public.charging_configs_id_seq'::regclass);


--
-- Name: payments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments ALTER COLUMN id SET DEFAULT nextval('public.payments_id_seq'::regclass);


--
-- Name: stations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations ALTER COLUMN id SET DEFAULT nextval('public.stations_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: admin_activity_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.admin_activity_logs (id, admin_id, action, details, "timestamp") FROM stdin;
\.


--
-- Data for Name: admin_stations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.admin_stations (admin_id, station_id) FROM stdin;
1	16
1	17
\.


--
-- Data for Name: admins; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.admins (id, username, email, hashed_password, is_super_admin, is_active, created_at, last_login) FROM stdin;
4	vedika	super@example.com	$2b$12$.6hFTq9Hbid6qfYNJ5i2vuhcrUmsiT13GXcTEZSl1XAe7Oz.dmj56	t	t	2025-04-12 18:46:37.265702	2025-04-13 01:10:13.844381
5	admin_test	admin_test@gmail.com	$2b$12$QzvKfbZW6Z.05JCf287gkuH5M7h5DSUP0CdwXA34eZrcHM35b3r9W	f	t	2025-04-12 18:49:39.945074	2025-04-13 01:15:35.389085
1	VedikaH	hedavedika@gmail.com	$2b$12$a1eU7QhZW5Gd/Qfklykx0.cQNyYmaRX3Gug0sVNgnB6r/.gen2.gi	t	t	2025-04-12 20:28:37.473249	2025-04-22 09:18:16.098757
\.


--
-- Data for Name: bookings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bookings (id, user_id, station_id, start_time, end_time, total_cost, status, created_at, updated_at, notes) FROM stdin;
\.


--
-- Data for Name: charging_configs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.charging_configs (id, station_id, charging_type, connector_type, power_output, cost_per_kwh) FROM stdin;
1	1	DC	CCS-2	60	13
2	1	DC	CCS-2	60	13
3	2	DC	CCS-2	60	13
4	2	DC	CCS-2	60	13
5	3	DC	CCS-2	60	13
6	3	DC	CCS-2	60	13
7	4	DC	CCS-2	60	13
8	4	DC	CCS-2	60	13
9	5	DC	CCS-2	60	13
10	5	DC	CCS-2	60	13
11	6	DC	CCS-2	60	13
12	6	DC	CCS-2	60	13
13	7	DC	CCS-2	60	13
14	7	DC	CCS-2	60	13
15	8	DC	CCS-2	60	13
16	8	DC	CCS-2	60	13
17	9	AC	Wall	9.9	18
18	9	AC	Wall	9.9	18
19	9	AC	Wall	9.9	18
20	9	AC	Wall	9.9	18
21	9	AC	Wall	9.9	18
22	9	AC	Wall	9.9	18
23	10	DC	GBT	15	18
24	11	DC	GBT	15	18
25	12	DC	GBT	15	14.99
26	13	DC	CCS-2	60	13
27	13	DC	CCS-2	60	13
28	14	DC	CCS-2	90	17.99
29	14	DC	CCS-2	90	17.99
30	14	DC	CCS-2	90	17.99
31	15	DC	CCS-2	60	13
32	15	DC	CCS-2	60	13
33	16	A	A	0	0
34	17	A	A	0	0
\.


--
-- Data for Name: payments; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payments (id, user_id, booking_id, order_id, amount, currency, status, created_at, updated_at, payment_method, transaction_id) FROM stdin;
\.


--
-- Data for Name: spatial_ref_sys; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text) FROM stdin;
\.


--
-- Data for Name: stations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stations (id, name, latitude, longitude, is_available, is_maintenance, location) FROM stdin;
1	Basheer Bagh EV Charger	17.404833	78.476712	t	f	Beside Liberty Bus Stop, Hyd, Hyderabad, Telangana, 500004, India
2	Tankbund road Opp. RK Math EV Charging Station	17.411769	78.48208	t	f	Ramakrishna Mattum, Lower Tankbund, Kavadiguda, Hyderabad, Telangana, 500029, India
3	Indira Park EV Charging Station	17.41156	78.48495	t	f	Gandhinagar, Lower Tank Bund, Kavadiguda, Hyderabad, Telangana, India
4	In Front of NTR Stadium, Parking 2nd Gate, Lower T	17.413127	78.485519	t	f	Indira Park, Near NTR Stadium, Hyderabad, Telangana, India
5	TS | Hyderabad | Courtyard By Marriott	17.423886	78.48799	t	f	Courtyard by Marriott Hyderabad, 1-3-1024, Lower Tank Bund Road, Hyderabad, Telangana, 500080, India
6	TS | Hyderabad | Marriott Hotel & Convention Centre	17.425165	78.48692	t	f	Marriott Hotel & Convention Centre, Tank Bund Road, Hyderabad, Telangana, 500080, India
7	Near LB Stadium EV Charging Station	17.399668	78.470924	t	f	Near LB Stadium, Hyderabad, Telangana, India
8	Gun foundry EV Charging Station	17.395958	78.475026	t	f	Gun Foundry, Hyderabad, Telangana, India
9	REIL Cipete Cherlapally Station	17.395451	78.472458	t	f	Board of Secondary Education (SSC), Hyderabad, Telangana, 500051, India
10	REIL VAMSHI FUEL POINT	17.396601	78.459846	t	f	Gandipet Main Road, Opp. Bapu Ghat Park, Langar Houz, Hyderabad, Telangana, 500008, India
11	REIL SAI PRIYA FILLING STATION	17.4093	78.498024	t	f	Musheerabad, Hyderabad, Telangana, 500020, India
12	GLIDA IOC Vidyanagar	17.402168	78.509141	t	f	1-9-1122/A, Opp. Durga Bai Deshmukh Hospital, Osmania University Rd, Vidya Nagar, Hyderabad, Telangana, 500044, India
13	Amberpet Police line Charging Station	17.387215	78.516632	t	f	Police Quarters, Police Lines, Hyderabad, Telangana, 500013, India
14	GLIDA HMR Moosarambagh	17.371318	78.511117	t	f	Moosarambagh, Hyderabad, Telangana, India
15	Esmayia Bazaar Charging Station	17.381872	78.491508	t	f	Near Chadharghar Bridge, Esamiya Bazar, Hyderabad, Telangana, 500027, India
16	TEST_STATION1	10	10	t	f	\N
17	TEST_STATION1	10	10	t	f	\N
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, email, hashed_password, created_at, updated_at, phone_number, is_active) FROM stdin;
1	john_doe	john@example.com	hashed_password_here	2025-02-05 01:27:25.526815+05:30	2025-02-05 01:27:25.526815+05:30	\N	\N
2	test1	test@example.com	$2b$12$5ZxrJ3mWgS96.3pMD8QJ6ew/TPC5N.iVe82pDlO/QncoETMyqNbCS	2025-04-17 00:45:04.296302+05:30	2025-04-17 00:45:04.296302+05:30	+1234567890	t
\.


--
-- Name: admin_activity_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admin_activity_logs_id_seq', 1, false);


--
-- Name: admins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admins_id_seq', 5, true);


--
-- Name: bookings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bookings_id_seq', 1, true);


--
-- Name: charging_configs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.charging_configs_id_seq', 35, true);


--
-- Name: payments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payments_id_seq', 1, false);


--
-- Name: stations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stations_id_seq', 18, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: admin_activity_logs admin_activity_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_activity_logs
    ADD CONSTRAINT admin_activity_logs_pkey PRIMARY KEY (id);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: charging_configs charging_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charging_configs
    ADD CONSTRAINT charging_configs_pkey PRIMARY KEY (id);


--
-- Name: payments payments_booking_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_booking_id_key UNIQUE (booking_id);


--
-- Name: payments payments_order_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_order_id_key UNIQUE (order_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: stations stations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stations
    ADD CONSTRAINT stations_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_phone_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_phone_number_key UNIQUE (phone_number);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: idx_stations_location; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stations_location ON public.stations USING gist (public.st_setsrid(public.st_makepoint(longitude, latitude), 4326));


--
-- Name: ix_admin_activity_logs_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_admin_activity_logs_id ON public.admin_activity_logs USING btree (id);


--
-- Name: ix_admins_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_admins_email ON public.admins USING btree (email);


--
-- Name: ix_admins_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_admins_id ON public.admins USING btree (id);


--
-- Name: ix_admins_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_admins_username ON public.admins USING btree (username);


--
-- Name: admin_activity_logs admin_activity_logs_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_activity_logs
    ADD CONSTRAINT admin_activity_logs_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.admins(id);


--
-- Name: admin_stations admin_stations_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_stations
    ADD CONSTRAINT admin_stations_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.admins(id);


--
-- Name: admin_stations admin_stations_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_stations
    ADD CONSTRAINT admin_stations_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id);


--
-- Name: bookings bookings_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id);


--
-- Name: bookings bookings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: charging_configs charging_configs_station_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.charging_configs
    ADD CONSTRAINT charging_configs_station_id_fkey FOREIGN KEY (station_id) REFERENCES public.stations(id);


--
-- Name: payments fk_booking; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_booking FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE SET NULL;


--
-- Name: payments fk_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payments payments_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE SET NULL;


--
-- Name: payments payments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


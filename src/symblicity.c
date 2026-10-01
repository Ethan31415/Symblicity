/* SPDX-License-Identifier: CC0-1.0 */
#define _POSIX_C_SOURCE 200809L
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

typedef uint8_t u8;
typedef long pos;
static char *s;
static pos n;
static int raw=0,input_wait_ms=-1,legacy_memory=0;
static struct termios oldt;

typedef struct {
	char **path;
	size_t count,selected;
	pid_t pid[2];
	int dual;
} Audio;
static Audio audio;

static void audio_stop(unsigned channel) {
	pid_t pid=audio.pid[channel];
	if(pid>0) {
		pid_t r;
		/*
		 * ffplay runs in its own session/process group (PGID == child PID).
		 * Kill the whole group so playback cannot survive if ffplay or its
		 * audio backend leaves a descendant behind.
		 */
		if(kill(-pid,SIGTERM)<0 && errno==ESRCH)
			(void)kill(pid,SIGTERM);
		do r=waitpid(pid,0,0); while(r<0&&errno==EINTR);
		audio.pid[channel]=0;
	}
}
static void audio_free(void) {
	audio_stop(0); audio_stop(1);
	for(size_t i=0;i<audio.count;i++) free(audio.path[i]);
	free(audio.path); audio.path=0; audio.count=audio.selected=0;
}
static int cmpstr(const void *a,const void *b) {
	const char *const *sa=a,*const *sb=b;
	return strcmp(*sa,*sb);
}
static int regular_file(const char *p) {
	struct stat st;
	return stat(p,&st)==0 && S_ISREG(st.st_mode);
}
static void audio_load_dir(const char *dir) {
	DIR *dp=opendir(dir); struct dirent *de;
	char **v=0; size_t len=0,cap=0;
	if(!dp) return;
	while((de=readdir(dp))!=0) {
		size_t dl,nl; char *p;
		if(de->d_name[0]=='.') continue;
		dl=strlen(dir); nl=strlen(de->d_name);
		p=malloc(dl+nl+2); if(!p) continue;
		memcpy(p,dir,dl);
		if(dl&&dir[dl-1]!='/') p[dl++]='/';
		memcpy(p+dl,de->d_name,nl+1);
		if(!regular_file(p)) { free(p); continue; }
		if(len==cap) {
			size_t nc=cap?cap*2:8;
			char **nv=realloc(v,nc*sizeof(*nv));
			if(!nv) { free(p); continue; }
			v=nv; cap=nc;
		}
		v[len++]=p;
	}
	closedir(dp);
	if(!len) { free(v); return; }
	qsort(v,len,sizeof(*v),cmpstr);
	audio.path=v; audio.count=len; audio.selected=0;
}
static void audio_play(unsigned channel) {
	pid_t p;
	if(!audio.count) return;
	audio_stop(channel);
	p=fork();
	if(p==0) {
		int fd;
		/* Audio must never compete with the VM for terminal input. */
		signal(SIGINT,SIG_DFL);
		signal(SIGTERM,SIG_DFL);
		(void)setsid();
		fd=open("/dev/null",O_RDONLY);
		if(fd>=0) {
			(void)dup2(fd,STDIN_FILENO);
			if(fd!=STDIN_FILENO) close(fd);
		}
		execlp("ffplay","ffplay","-nodisp","-autoexit",
			"-volume","100","-loglevel","error",
			audio.path[audio.selected],(char *)0);
		_exit(127);
	}
	if(p>0) audio.pid[channel]=p;
}
static void restore(void) { audio_free();
	if(raw) tcsetattr(STDIN_FILENO,TCSANOW,&oldt); }
static void caught(int sig) { restore(); _exit(128+sig); }

static char *load(const char *p) {
	FILE *f=fopen(p,"rb"); long z; char *b; pos r=0;
	if(!f) return 0;
	fseek(f,0,SEEK_END); z=ftell(f); rewind(f);
	if(z<0 || !(b=malloc((size_t)z+1))) { fclose(f); return 0; }
	z=(long)fread(b,1,(size_t)z,f); fclose(f);
	b[z]=0;
	if(strstr(b,"\t@memory legacy-2x256")) legacy_memory=1;
	for(long i=0;i<z;i++) {
		if(b[i]=='\t') { while(i+1<z&&b[i+1]!='\n'&&b[i+1]!='\r') i++; continue; }
		if(b[i]=='\n'||b[i]=='\r'||b[i]=='\f'||b[i]=='\v') continue;
		b[r++]=b[i];
	}
	b[r]=0; n=r; return b;
}
static pos findc(pos p,int d,char c) {
	for(p+=d;p>=0&&p<n;p+=d) if(s[p]==c) return p;
	return -1;
}
static pos letter(pos p,int d,char c) {
	char q=islower((unsigned char)c)?
		(char)toupper((unsigned char)c):(char)tolower((unsigned char)c);
	return findc(p,d,q);
}
static pos pair(pos p,int d,char same,char other) {
	int depth=1;
	for(p+=d;p>=0&&p<n;p+=d) {
		if(s[p]==same) depth++;
		else if(s[p]==other && !--depth) return p;
	}
	return -1;
}
/* '~' breaks only the innermost enclosing [] loop. */
static pos leave_loop(pos p,int d) {
	int depth=0; pos q;
	if(d>0) {
		for(pos i=p-1;i>=0;i--) {
			if(s[i]==']') depth++;
			else if(s[i]=='[') {
				if(depth) depth--;
				else if((q=pair(i,1,'[',']'))>p) return q+1;
			}
		}
	} else {
		for(pos i=p+1;i<n;i++) {
			if(s[i]=='[') depth++;
			else if(s[i]==']') {
				if(depth) depth--;
				else if((q=pair(i,-1,']','['))>=0&&q<p) return q-1;
			}
		}
	}
	return p+d;
}
static int read_byte_wait(unsigned char *out) {
	struct pollfd pfd={STDIN_FILENO,POLLIN,0};
	int r; ssize_t got;
	do r=poll(&pfd,1,input_wait_ms); while(r<0&&errno==EINTR);
	if(r==0) return 0;
	if(r<0) return -1;
	do got=read(STDIN_FILENO,out,1); while(got<0&&errno==EINTR);
	if(got==1) return 1;
	if(got==0) return -1;
	if(errno==EAGAIN||errno==EWOULDBLOCK) return 0;
	return -1;
}
static int readchar_timed(u8 *out) {
	unsigned char c;
	if(read_byte_wait(&c)!=1) return 0;
	*out=(u8)c; return 1;
}
static u8 readnum(void) {
	char b[64],*e; long x;
	if(scanf("%63s",b)!=1) { clearerr(stdin); return 0; }
	x=strtol(b,&e,10); return e==b?0:(u8)x;
}
static int readnum_timed(u8 *out) {
	char b[64],*e; size_t len=0; long x;
	unsigned char c; int rc;
	for(;;) {
		rc=read_byte_wait(&c);
		if(rc<=0) return 0;
		if(!isspace((unsigned char)c)) break;
	}
	for(;;) {
		if(len+1<sizeof(b)) b[len++]=(char)c;
		rc=read_byte_wait(&c);
		if(rc==0) return 0;
		if(rc<0||isspace((unsigned char)c)) break;
	}
	b[len]=0;
	x=strtol(b,&e,10);
	*out=e==b?0:(u8)x;
	return 1;
}
#define SYSTEM_TIME_ADDR 0xFEFFu
#define DATA_FILE_NAME_BASE 0xFF00u

static u8 wrapped_system_time(void) {
	struct timespec ts;
	uint64_t ms;
	if(clock_gettime(CLOCK_REALTIME,&ts)!=0) return 0;
	ms=(uint64_t)ts.tv_sec*1000u+(uint64_t)ts.tv_nsec/1000000u;
	return (u8)ms;
}

typedef struct {
	FILE *fp;
	char name[256];
} DataFile;

static int data_file_name(const u8 *mem,char out[256]) {
	for(size_t i=0;i<256;i++) {
		u8 b=mem[DATA_FILE_NAME_BASE+i];
		if(!b) {
			out[i]=0;
			return i?1:0;
		}
		out[i]=(char)b;
	}
	return -1;
}

static int data_file_prepare(DataFile *f,const u8 *mem,int create) {
	char name[256]; int rc=data_file_name(mem,name);
	FILE *fp;
	if(rc==0) {
		fputs("sym: empty file name at 0xFF00\n",stderr);
		return 0;
	}
	if(rc<0) {
		fputs("sym: file name at 0xFF00 is not NUL-terminated within 256 bytes\n",stderr);
		return 0;
	}
	if(f->fp&&!strcmp(f->name,name)) return 1;
	if(f->fp) {
		(void)fclose(f->fp);
		f->fp=0;
		f->name[0]=0;
	}
	errno=0;
	fp=fopen(name,"r+b");
	if(!fp&&create&&errno==ENOENT) fp=fopen(name,"w+b");
	if(!fp) {
		fprintf(stderr,"sym: file '%s': %s\n",name,strerror(errno));
		return 0;
	}
	f->fp=fp;
	memcpy(f->name,name,strlen(name)+1);
	return 1;
}

static int data_file_barrier(DataFile *f) {
	if(fseek(f->fp,0,SEEK_CUR)==0) return 1;
	fprintf(stderr,"sym: file '%s': %s\n",f->name,strerror(errno));
	return 0;
}

static int parse_input_wait(const char *text,int *out) {
	char *end; long ms;
	if(!strcmp(text,"infinite")||!strcmp(text,"inf")||!strcmp(text,"-1")) {
		*out=-1; return 1;
	}
	errno=0; ms=strtol(text,&end,10);
	if(errno||*end||ms<0||ms>60000) return 0;
	*out=(int)ms; return 1;
}
static int memory_letter(char c) { return strchr("wWxXyYzZ",c)!=0; }
static int audio_letter(char c) {
	if(!audio.count) return 0;
	if(strchr("uUvV",c)) return 1;
	return audio.dual&&strchr("tT",c)!=0;
}
static int reserved_letter(char c) { return memory_letter(c)||audio_letter(c); }

int main(int ac,char **av) {
	int buffered=1,arg=1; char *file=0;
	const char *sound_dir=0;
	struct termios rawt;
	atexit(restore);
	signal(SIGINT,caught);
	signal(SIGTERM,caught);
	signal(SIGHUP,caught);
	signal(SIGQUIT,caught);
	for(;arg<ac;arg++) {
		if(!strcmp(av[arg],"-u")||!strcmp(av[arg],"--unbuffered")) buffered=0;
		else if(!strcmp(av[arg],"-B")||!strcmp(av[arg],"--buffered")) buffered=1;
		else if(!strcmp(av[arg],"-n")||!strcmp(av[arg],"--nonblocking")) input_wait_ms=0;
		else if(!strcmp(av[arg],"-b")||!strcmp(av[arg],"--blocking")) input_wait_ms=-1;
		else if(!strcmp(av[arg],"--input-wait")||!strcmp(av[arg],"--input-timeout")) {
			const char *flag=av[arg];
			if(++arg>=ac) {
				fprintf(stderr,"sym: %s requires milliseconds or infinite\n",flag); return 1;
			}
			if(!parse_input_wait(av[arg],&input_wait_ms)) {
				fprintf(stderr,"sym: %s must be infinite, -1, or 0..60000 ms\n",flag); return 1;
			}
		}
		else if(!strcmp(av[arg],"-2")||!strcmp(av[arg],"--dual-audio")) audio.dual=1;
		else if(!strcmp(av[arg],"-s")||!strcmp(av[arg],"--sounds")) {
			if(++arg>=ac) { fputs("sym: --sounds requires a directory\n",stderr); return 1; }
			sound_dir=av[arg];
		} else if(!strcmp(av[arg],"-h")||!strcmp(av[arg],"--help")) {
			puts("Usage: sym [-u|-B] [--input-wait MS|infinite] [-s DIR] [-2] <program.sym>\n"
				 "  -u --unbuffered   immediate TTY input; disable canonical buffering/echo\n"
				 "  -B --buffered     enable/default stdin buffering\n"
				 "  -n --nonblocking  same as --input-wait 0\n"
				 "  -b --blocking     same as --input-wait infinite (default)\n"
				 "  --input-wait X    infinite/-1 blocks; 0 polls; N waits N milliseconds\n"
				 "  --input-timeout X compatibility alias for --input-wait\n"
				 "  -s --sounds DIR   load sorted sounds for async audio\n"
				 "  -2 --dual-audio   enable T/t as channel-2 play/stop");
			return 0;
		} else if(!file) file=av[arg]; else {
			fputs("sym: too many input files\n",stderr); return 1;
		}
	}
	if(!file) { fputs("Usage: sym [-u|-B] [--input-wait MS|infinite] [-s DIR] [-2] <program.sym>\n",stderr); return 1; }
	if(sound_dir) audio_load_dir(sound_dir);
	if(!buffered) {
		setvbuf(stdin,0,_IONBF,0);
		if(isatty(STDIN_FILENO)&&tcgetattr(STDIN_FILENO,&oldt)==0) {
			rawt=oldt; rawt.c_lflag&=(tcflag_t)~(ICANON|ECHO);
			rawt.c_cc[VMIN]=1; rawt.c_cc[VTIME]=0;
			if(tcsetattr(STDIN_FILENO,TCSANOW,&rawt)==0) raw=1;
		}
	}
	if(!(s=load(file))) { perror(file); return 1; }

	u8 r[5]={0},aw=0,ay=0,st[4096],t;
	static u8 mem[65536];
	u8 *A=&r[0],*B=&r[1];
	size_t head=0,sp=0,mask=4095;
	int bottom=0,d=1;
	pos pc=0,q,ret_stack[4096]; size_t rsp=0; char caller=0;
	DataFile data_file={0};

	while(pc>=0&&pc<n) {
		char o=s[pc];

		if(o==' ') { pc+=2*d; continue; }

		if(isalpha((unsigned char)o)&&!reserved_letter(o)) {
			q=letter(pc,d,o); pc=q<0?pc+d:q; continue;
		}

		switch(o) {
		case '0':case '1':case '2':case '3':case '4':case '5':case '6':case '7':
			*A+=(u8)(1u<<(o-'0')); break;
		case '8': --*A; break;
		case '9': *A-=2; break;

		case '+': r[2]=(u8)(*A+*B); break;
		case '-': r[2]=(u8)(*A-*B); break;
		case '*': r[2]=(u8)(*A**B); break;
		case '/': r[2]=*B?(u8)(*A/ *B):0; break;
		case '%': r[2]=*B?(u8)(*A% *B):0; break;
		case '^': r[2]=(u8)(*A^*B); break;
		case '|': r[2]=(u8)(*A|*B); break;
		case '&': r[2]=(u8)(*A&*B); break;

		case '=': pc+=(*A==*B)*d; break;
		case '<': pc+=(*A< *B)*d; break;
		case '>': pc+=(*A> *B)*d; break;
		case '!': pc+=(*A!=*B)*d; break;
		case '?': pc+=(r[2]==0)*d; break;
		case ':': t=*A; *A=*B; *B=t; break;
		case ';': t=*B; *B=r[2]; r[2]=t; break;
		case '\\':
			if(A==&r[0]) A=&r[3],B=&r[4]; else A=&r[0],B=&r[1];
			break;

		case '@':
			if(sp==4096) { fputs("sym: stack overflow\n",stderr); free(s); return 1; }
			if(bottom) head=(head-1)&mask,st[head]=*A;
			else st[(head+sp)&mask]=*A;
			sp++; break;
		case '$':
			if(!sp) *A=0;
			else if(bottom) *A=st[head],head=(head+1)&mask,sp--;
			else *A=st[(head+--sp)&mask];
			break;
		case '_': bottom=!bottom; break;

		case '\'':
			if(input_wait_ms<0) {
				int c=getchar(); *A=(u8)(c==EOF?0:c); if(c==EOF) clearerr(stdin);
			} else {
				u8 v; if(readchar_timed(&v)) { *A=v; r[2]=1; } else r[2]=0;
			}
			break;
		case '"': putchar(*A); fflush(stdout); break;
		case '.':
			if(input_wait_ms<0) *A=readnum();
			else {
				u8 v; if(readnum_timed(&v)) { *A=v; r[2]=1; } else r[2]=0;
			}
			break;
		case ',': printf("%u",(unsigned)*A); fflush(stdout); break;

		case 'w': aw=*A; break;           case 'W': *A=aw; break;
		case 'y': ay=*A; break;           case 'Y': *A=ay; break;
		case 'x': {
			uint16_t addr=legacy_memory ? (uint16_t)aw
				: ((uint16_t)aw|((uint16_t)ay<<8));
			if(legacy_memory||addr!=SYSTEM_TIME_ADDR) mem[addr]=*A;
			break;
		}
		case 'X': {
			uint16_t addr=legacy_memory ? (uint16_t)aw
				: ((uint16_t)aw|((uint16_t)ay<<8));
			*A=(!legacy_memory&&addr==SYSTEM_TIME_ADDR)
				? wrapped_system_time() : mem[addr];
			break;
		}
		case 'z':
		case 'Z':
			if(legacy_memory) {
				if(o=='z') mem[(uint16_t)(0x100u|ay)]=*A;
				else *A=mem[(uint16_t)(0x100u|ay)];
				break;
			}
			if(!data_file_prepare(&data_file,mem,o=='z')||
			   !data_file_barrier(&data_file)) {
				free(s); return 1;
			}
			if(o=='z') {
				if(fputc(*A,data_file.fp)==EOF||fflush(data_file.fp)==EOF) {
					fprintf(stderr,"sym: file '%s': %s\n",
						data_file.name,strerror(errno));
					free(s); return 1;
				}
				r[2]=0;
			} else {
				int v=fgetc(data_file.fp);
				if(v==EOF) {
					if(feof(data_file.fp)) {
						clearerr(data_file.fp);
						r[2]=1;
					} else {
						fprintf(stderr,"sym: file '%s': %s\n",
							data_file.name,strerror(errno));
						free(s); return 1;
					}
				} else {
					*A=(u8)v;
					r[2]=0;
				}
			}
			break;

		case 'U':
			if(audio.count) audio.selected=(audio.selected+1)%audio.count;
			break;
		case 'u':
			if(audio.count) audio.selected=(audio.selected+audio.count-1)%audio.count;
			break;
		case 'V': audio_play(0); break;
		case 'v': audio_stop(0); break;
		case 'T': audio_play(1); break;
		case 't': audio_stop(1); break;

		case '#': pc+=((pos)*A+1)*d; continue;
		case '{': d=1; pc++; continue;
		case '}': d=-1; pc--; continue;
		case '[':
			if(d<0&&(q=pair(pc,1,'[',']'))>=0) { pc=q-1; continue; }
			break;
		case ']':
			if(d>0&&(q=pair(pc,-1,']','['))>=0) { pc=q+1; continue; }
			break;
		case '~': pc=leave_loop(pc,d); continue;

		case '(':
		case ')':
			if(rsp&&o!=caller) {
				pc=ret_stack[--rsp]+d;
				if(!rsp) caller=0;
				continue;
			}
			if(!rsp) caller=o;
			if(rsp==4096) {
				fputs("sym: return stack overflow\n",stderr);
				free(s); return 1;
			}
			ret_stack[rsp++]=pc;
			break;

		case '`': *A=0; break;

		default:
			fprintf(stderr,"sym: invalid character 0x%02X at %ld\n",
					(unsigned char)o,pc);
			free(s); return 1;
		}
		pc+=d;
	}
	if(data_file.fp) (void)fclose(data_file.fp);
	free(s); return 0;
}

      SUBROUTINE MG5_1_GOLEMLOOP(NLOOPLINE,PL,M2L,RANK,RES,STABLE)
C     
C     Generated by MadGraph5_aMC@NLO v. %(version)s, %(date)s
C     By the MadGraph5_aMC@NLO Development Team
C     Visit launchpad.net/madgraph5 and amcatnlo.web.cern.ch
C     
C     Interface between MG5 and Golem95.
C     The Golem95 version should be higher than 1.3.0.
C     It supports RANK = NLOOPLINE + 1 tensor integrals when 1 <
C      NLOOPLINE < 6.
C     
C     Process: u u~ > u u~ [ virt = QCD ] @1
C     
C     
C     MODULES
C     
      USE MATRICE_S
      USE FORM_FACTOR_TYPE, ONLY: FORM_FACTOR
      USE PRECISION_GOLEM, ONLY: KI
      USE TENS_COMB
      USE TENS_REC
      USE FORM_FACTOR_1P, ONLY: A10
      USE FORM_FACTOR_2P, ONLY: A20
      USE FORM_FACTOR_3P, ONLY: A30
      USE FORM_FACTOR_4P, ONLY: A40
      USE FORM_FACTOR_5P, ONLY: A50
      USE FORM_FACTOR_6P, ONLY: A60
      IMPLICIT NONE
C     
C     CONSTANTS 
C     
      INTEGER    NEXTERNAL
      PARAMETER (NEXTERNAL=4)
      LOGICAL CHECKPCONSERVATION
      PARAMETER (CHECKPCONSERVATION=.TRUE.)
      REAL*8 NORMALIZATION
      PARAMETER (NORMALIZATION = 1.D0/(16.D0*3.14159265358979323846D0*
     $ *2))
      REAL(KI),DIMENSION(0:3),PARAMETER::NULL_VEC = (/0.0_KI,0.0_KI
     $ ,0.0_KI,0.0_KI/)
C     GOLEM_RUN_MODE = 1: Use directly MadLoop tensorial coefficients
C     GOLEM_RUN_MODE = 2: Reconstruct the tensorial coefficeints
C      directly from 
C     numerator using golem internal reconstruction routine
C     GOLEM_RUN_MODE = 3: Cross-checked reconstructed coefficients
C      against
C     MadLoop internal ones.
      INTEGER GOLEM_RUN_MODE
      PARAMETER (GOLEM_RUN_MODE=1)
C     The following is the acceptance threshold used for GOLEM_RUN_MODE
C      = 3
      REAL*8 COEF_CHECK_THRS
      DATA COEF_CHECK_THRS/1.0D-13/
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS

      LOGICAL PASS_COEF_CHECK
C     
C     ARGUMENTS 
C     
      INTEGER NLOOPLINE, RANK
      REAL*8 PL(0:3,NLOOPLINE)
      REAL*8 PCT(0:3,0:NLOOPLINE-1)
      REAL(KI) PGOLEM(NLOOPLINE,0:3)
      COMPLEX*16 M2L(NLOOPLINE)
      COMPLEX(KI) M2LGOLEM(NLOOPLINE)
      COMPLEX*16 RES(3)
      LOGICAL STABLE
C     
C     LOCAL VARIABLES 
C     
      INTEGER I, J, K
      TYPE(FORM_FACTOR)::RES_GOLEM

      COMPLEX(KI)::COEFFS0,COEFFS0_REC
      TYPE(COEFF_TYPE_1)::COEFFS1,COEFFS1_REC
      TYPE(COEFF_TYPE_2)::COEFFS2,COEFFS2_REC
      TYPE(COEFF_TYPE_3)::COEFFS3,COEFFS3_REC
      TYPE(COEFF_TYPE_4)::COEFFS4,COEFFS4_REC
      TYPE(COEFF_TYPE_5)::COEFFS5,COEFFS5_REC
      TYPE(COEFF_TYPE_6)::COEFFS6,COEFFS6_REC

C     The pinch propagator optimization is not used, so for now it is
C     always 0.
      INTEGER PINCH
C     
C     EXTERNAL FUNCTIONS
C     
      COMPLEX(KI) MG5_1_GOLEM_LOOPNUM
      EXTERNAL MG5_1_GOLEM_LOOPNUM
      LOGICAL MG5_1_COMPARE_COEFS_0
      LOGICAL MG5_1_COMPARE_COEFS_1
      LOGICAL MG5_1_COMPARE_COEFS_2
      LOGICAL MG5_1_COMPARE_COEFS_3
      LOGICAL MG5_1_COMPARE_COEFS_4
      LOGICAL MG5_1_COMPARE_COEFS_5
      LOGICAL MG5_1_COMPARE_COEFS_6
C     
C     GLOBAL VARIABLES
C     
      INCLUDE 'coupl.inc'
      INTEGER CTMODE
      REAL*8 LSCALE
      COMMON/MG5_1_CT/LSCALE,CTMODE

      INTEGER ID,SQSOINDEX,R
      COMMON/MG5_1_LOOP/ID,SQSOINDEX,R

      LOGICAL CTINIT, TIRINIT, GOLEMINIT, SAMURAIINIT, NINJAINIT
      COMMON/REDUCTIONCODEINIT/CTINIT, TIRINIT,GOLEMINIT,SAMURAIINIT
     $ ,NINJAINIT

      INTEGER NLOOPGROUPS
      PARAMETER (NLOOPGROUPS=13)
      INTEGER NSQUAREDSO
      PARAMETER (NSQUAREDSO=1)
      INCLUDE 'loop_max_coefs.inc'

      COMPLEX*16 LOOPCOEFS(0:LOOPMAXCOEFS-1,NSQUAREDSO,NLOOPGROUPS)
      COMMON/MG5_1_LCOEFS/LOOPCOEFS
C     ----------
C     BEGIN CODE
C     ----------

C     The CT initialization is also performed here if not done already
C      because it calls MPINIT of OneLOop which is necessary on some
C      system
      IF (CTINIT) THEN
        CTINIT=.FALSE.
        CALL MG5_1_INITCT()
      ENDIF

C     INITIALIZE GOLEM IF NEEDED
      IF (GOLEMINIT) THEN
        GOLEMINIT=.FALSE.
        CALL MG5_1_INITGOLEM()
      ENDIF

C     No stability test intrisic to Golem95 now
      STABLE=.TRUE.

C     This initialization must be done for each reduction because we
C     have not setup anyoptimization using pinched propagators yet.
      CALL INITGOLEM95(NLOOPLINE)
      PINCH = 0

C     YOU CAN FIND THE DETAILS ABOUT THE DIFFERENT CTMODE AT THE
C      BEGINNING OF THE FILE CTS_CUTS.F90 IN THE CUTTOOLS DISTRIBUTION

C     CONVERT THE MASSES TO BE COMPLEX
      DO I=1,NLOOPLINE
        M2LGOLEM(I)=M2L(I)
      ENDDO

C     CONVERT THE MOMENTA FLOWING IN THE LOOP LINES TO CT CONVENTIONS
      DO I=0,3
        DO J=0,(NLOOPLINE-1)
          PCT(I,J)=0.D0
        ENDDO
      ENDDO
      DO I=0,3
        DO J=1,NLOOPLINE
          PCT(I,0)=PCT(I,0)+PL(I,J)
        ENDDO
      ENDDO
      IF (CHECKPCONSERVATION) THEN
        IF (PCT(0,0).GT.1.D-6) THEN
          WRITE(*,*) 'energy is not conserved ',PCT(0,0)
          STOP 'energy is not conserved'
        ELSEIF (PCT(1,0).GT.1.D-6) THEN
          WRITE(*,*) 'px is not conserved ',PCT(1,0)
          STOP 'px is not conserved'
        ELSEIF (PCT(2,0).GT.1.D-6) THEN
          WRITE(*,*) 'py is not conserved ',PCT(2,0)
          STOP 'py is not conserved'
        ELSEIF (PCT(3,0).GT.1.D-6) THEN
          WRITE(*,*) 'pz is not conserved ',PCT(3,0)
          STOP 'pz is not conserved'
        ENDIF
      ENDIF
      DO I=0,3
        DO J=1,(NLOOPLINE-1)
          DO K=1,J
            PCT(I,J)=PCT(I,J)+PL(I,K)
          ENDDO
        ENDDO
      ENDDO

C     Now convert the loop momenta to Golem95 conventions
      DO I=0,3
        PGOLEM(1,I)=0.0E0_KI
        DO J=2,NLOOPLINE
          PGOLEM(J,I)=PCT(I,J-1)
        ENDDO
      ENDDO

C     Fill in the kinematic s-matrix while taking care of on-shell
C      limits.
      CALL MG5_1_SETUP_KIN_MATRIX(NLOOPLINE,PGOLEM,M2LGOLEM)
C     Construct the golem internal matrices derived from the kinetic
C      one.
      CALL PREPARESMATRIX()

C     Fill in the golem coefficents and compute the loop
      IF(GOLEM_RUN_MODE.EQ.2)THEN
        RES_GOLEM = EVALUATE_B(MG5_1_GOLEM_LOOPNUM,PGOLEM,0,RANK)
      ELSE
        PASS_COEF_CHECK=.TRUE.
        SELECT CASE(RANK)
        CASE(0)
        CALL MG5_1_FILL_GOLEM_COEFFS_0(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS0)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          COEFFS0_REC = MG5_1_GOLEM_LOOPNUM(NULL_VEC,0.0_KI)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_0(COEFFS0,COEFFS0_REC)
        ENDIF
        CASE(1)
        CALL MG5_1_FILL_GOLEM_COEFFS_1(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS1)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT1(MG5_1_GOLEM_LOOPNUM,COEFFS1_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_1(COEFFS1,COEFFS1_REC)
        ENDIF
        CASE(2)
        CALL MG5_1_FILL_GOLEM_COEFFS_2(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS2)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT2(MG5_1_GOLEM_LOOPNUM,COEFFS2_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_2(COEFFS2,COEFFS2_REC)
        ENDIF
        CASE(3)
        CALL MG5_1_FILL_GOLEM_COEFFS_3(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS3)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT3(MG5_1_GOLEM_LOOPNUM,COEFFS3_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_3(COEFFS3,COEFFS3_REC)
        ENDIF
        CASE(4)
        CALL MG5_1_FILL_GOLEM_COEFFS_4(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS4)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT4(MG5_1_GOLEM_LOOPNUM,COEFFS4_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_4(COEFFS4,COEFFS4_REC)
        ENDIF
        CASE(5)
        CALL MG5_1_FILL_GOLEM_COEFFS_5(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS5)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT5(MG5_1_GOLEM_LOOPNUM,COEFFS5_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_5(COEFFS5,COEFFS5_REC)
        ENDIF
        CASE(6)
        CALL MG5_1_FILL_GOLEM_COEFFS_6(LOOPCOEFS(0,SQSOINDEX,ID)
     $   ,COEFFS6)
        IF(GOLEM_RUN_MODE.EQ.3)THEN
          CALL RECONSTRUCT6(MG5_1_GOLEM_LOOPNUM,COEFFS6_REC)
          PASS_COEF_CHECK=MG5_1_COMPARE_COEFS_6(COEFFS6,COEFFS6_REC)
        ENDIF
        CASE DEFAULT
        WRITE(*,*)'Not yet implemented in Golem95 for rank= ',RANK
        STOP
        END SELECT

        IF(.NOT.PASS_COEF_CHECK)THEN
          WRITE(*,*)'Coefs mismatch for ID ',ID,' and rank ',RANK
          WRITE(*,*)'Coefs form MadLoop5:'
          SELECT CASE(RANK)
          CASE(0)
          WRITE(*,*)'Constant coef = ',COEFFS0
          CASE(1)
          CALL PRINT_COEFFS(COEFFS1)
          CASE(2)
          CALL PRINT_COEFFS(COEFFS2)
          CASE(3)
          CALL PRINT_COEFFS(COEFFS3)
          CASE(4)
          CALL PRINT_COEFFS(COEFFS4)
          CASE(5)
          CALL PRINT_COEFFS(COEFFS5)
          CASE(6)
          CALL PRINT_COEFFS(COEFFS6)
          END SELECT
          WRITE(*,*)'Coefs reconstructed by Golem95:'
          SELECT CASE(RANK)
          CASE(0)
          WRITE(*,*)'Constant coef = ',COEFFS0_REC
          CASE(1)
          CALL PRINT_COEFFS(COEFFS1_REC)
          CASE(2)
          CALL PRINT_COEFFS(COEFFS2_REC)
          CASE(3)
          CALL PRINT_COEFFS(COEFFS3_REC)
          CASE(4)
          CALL PRINT_COEFFS(COEFFS4_REC)
          CASE(5)
          CALL PRINT_COEFFS(COEFFS5_REC)
          CASE(6)
          CALL PRINT_COEFFS(COEFFS6_REC)
          END SELECT
          STOP
        ENDIF

        SELECT CASE(NLOOPLINE)
        CASE(1)
        WRITE(*,*)'Golem95 cannot handle with tadpole yet'
        STOP
        CASE(2)
        SELECT CASE(RANK)
        CASE(0)
        RES_GOLEM = COEFFS0*A20(PINCH)
        CASE(1)
        RES_GOLEM = CONTRACT2_1(COEFFS1,PGOLEM,PINCH)
        CASE(2)
        RES_GOLEM = CONTRACT2_2(COEFFS2,PGOLEM,PINCH)
        CASE(3)
        RES_GOLEM = CONTRACT2_3(COEFFS3,PGOLEM,PINCH)
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N,r = ',2,RANK
        STOP
        END SELECT
        CASE(3)
        SELECT CASE(RANK)
        CASE(0)
        RES_GOLEM = COEFFS0*A30(PINCH)
        CASE(1)
        RES_GOLEM = CONTRACT3_1(COEFFS1,PGOLEM,PINCH)
        CASE(2)
        RES_GOLEM = CONTRACT3_2(COEFFS2,PGOLEM,PINCH)
        CASE(3)
        RES_GOLEM = CONTRACT3_3(COEFFS3,PGOLEM,PINCH)
        CASE(4)
        RES_GOLEM = CONTRACT3_4(COEFFS4,PGOLEM,PINCH)
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N,r = ',3,RANK
        STOP
        END SELECT
        CASE(4)
        SELECT CASE(RANK)
        CASE(0)
        RES_GOLEM = COEFFS0*A40(PINCH)
        CASE(1)
        RES_GOLEM = CONTRACT4_1(COEFFS1,PGOLEM,PINCH)
        CASE(2)
        RES_GOLEM = CONTRACT4_2(COEFFS2,PGOLEM,PINCH)
        CASE(3)
        RES_GOLEM = CONTRACT4_3(COEFFS3,PGOLEM,PINCH)
        CASE(4)
        RES_GOLEM = CONTRACT4_4(COEFFS4,PGOLEM,PINCH)
        CASE(5)
        RES_GOLEM = CONTRACT4_5(COEFFS5,PGOLEM,PINCH)
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N,r = ',4,RANK
        STOP
        END SELECT
        CASE(5)
        SELECT CASE(RANK)
        CASE(0)
        RES_GOLEM = COEFFS0*A50(PINCH)
        CASE(1)
        RES_GOLEM = CONTRACT5_1(COEFFS1,PGOLEM,PINCH)
        CASE(2)
        RES_GOLEM = CONTRACT5_2(COEFFS2,PGOLEM,PINCH)
        CASE(3)
        RES_GOLEM = CONTRACT5_3(COEFFS3,PGOLEM,PINCH)
        CASE(4)
        RES_GOLEM = CONTRACT5_4(COEFFS4,PGOLEM,PINCH)
        CASE(5)
        RES_GOLEM = CONTRACT5_5(COEFFS5,PGOLEM,PINCH)
        CASE(6)
        RES_GOLEM = CONTRACT5_6(COEFFS6,PGOLEM,PINCH)
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N,r = ',5,RANK
        STOP
        END SELECT
        CASE(6)
        SELECT CASE(RANK)
        CASE(0)
        RES_GOLEM = COEFFS0*A60(PINCH)
        CASE(1)
        RES_GOLEM = CONTRACT6_1(COEFFS1,PGOLEM,PINCH)
        CASE(2)
        RES_GOLEM = CONTRACT6_2(COEFFS2,PGOLEM,PINCH)
        CASE(3)
        RES_GOLEM = CONTRACT6_3(COEFFS3,PGOLEM,PINCH)
        CASE(4)
        RES_GOLEM = CONTRACT6_4(COEFFS4,PGOLEM,PINCH)
        CASE(5)
        RES_GOLEM = CONTRACT6_5(COEFFS5,PGOLEM,PINCH)
        CASE(6)
        RES_GOLEM = CONTRACT6_6(COEFFS6,PGOLEM,PINCH)
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N,r = ',6,RANK
        STOP
        END SELECT
        CASE DEFAULT
        WRITE(*,*)'Golem95 cannot handle with: N = ',NLOOPLINE
        STOP
        END SELECT
      ENDIF

      RES(1)=NORMALIZATION*2.0D0*DBLE(RES_GOLEM%%C+2.0*LOG(MU_R)
     $ *RES_GOLEM%%B+2.0*LOG(MU_R)**2*RES_GOLEM%%A)
      RES(2)=NORMALIZATION*2.0D0*DBLE(RES_GOLEM%%B+2.0*LOG(MU_R)
     $ *RES_GOLEM%%A)
      RES(3)=NORMALIZATION*2.0D0*DBLE(RES_GOLEM%%A)
C     WRITE(*,*) 'Loop ID',ID,' =',RES(1),RES(2),RES(3)

C     Finally free golem memory and cache
      CALL EXITGOLEM95()

      END

      FUNCTION MG5_1_GOLEM_LOOPNUM(Q,MU2)
      USE PRECISION_GOLEM, ONLY: KI
      REAL(KI),DIMENSION(0:3),INTENT(IN)::Q
      REAL(KI),INTENT(IN)::MU2
      COMPLEX(KI)::MG5_1_GOLEM_LOOPNUM

      COMPLEX*16 QQ(0:3),NUM
      INTEGER I

      DO I=0,3
        QQ(I)=CMPLX(Q(I),0.0D0,KIND=16)
      ENDDO

      CALL MG5_1_LOOPNUM(QQ,NUM)
      MG5_1_GOLEM_LOOPNUM=NUM
      RETURN
      END FUNCTION

      SUBROUTINE MG5_1_INITGOLEM()
C     
C     INITIALISATION OF GOLEM
C     
C     
C     MODULE
C     
      USE PARAMETRE
C     
C     LOCAL VARIABLES 
C     
      REAL*8 THRS
      LOGICAL EXT_NUM_FOR_R1
C     
C     GLOBAL VARIABLES 
C     
      INCLUDE 'MadLoopParams.inc'
C     ----------
C     BEGIN CODE
C     ----------

C     DEFAULT PARAMETERS FOR GOLEM
C     -------------------------------  
C     One can chose here to have either just the rational R1 piece 
C     or everything but the R2
      RAT_OR_TOT_PAR = TOT

      END

      SUBROUTINE MG5_1_SETUP_KIN_MATRIX(NLOOPLINE,PGOLEM,M2L)
C     
C     MODULE
C     
      USE MATRICE_S
      USE PRECISION_GOLEM, ONLY: KI
C     
C     ARGUMENTS
C     
      INTEGER NLOOPLINE
      REAL(KI) PGOLEM(NLOOPLINE,0:3)
      COMPLEX(KI) M2L(NLOOPLINE)
C     
C     LOCAL VARIABLES
C     
      INTEGER I,J
      COMPLEX*16 S_MAT_FROM_MG(NLOOPLINE,NLOOPLINE)
C     ----------
C     BEGIN CODE
C     ----------

      CALL MG5_1_BUILD_KINEMATIC_MATRIX(NLOOPLINE,PGOLEM,M2L,S_MAT_FROM
     $ _MG)

      DO I=1,NLOOPLINE
        DO J=1,NLOOPLINE
          S_MAT(I,J)=S_MAT_FROM_MG(I,J)
        ENDDO
      ENDDO

      END

      FUNCTION MG5_1_COMPARE_COEFS_0(COEFS_A,COEFS_B)

      USE PRECISION_GOLEM, ONLY: KI
      COMPLEX(KI) COEFS_A,COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_0

      NUM = ABS(COEFS_A-COEFS_B)
      DENOM = ABS(COEFS_A+COEFS_B)
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_0=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_0=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_1(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_1)COEFS_A,COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_1

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))

      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_1=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_1=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_2(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_2) COEFS_A,COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_2

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
     $ +SUM(ABS(COEFS_A%%C2-COEFS_B%%C2))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))+SUM(ABS(COEFS_A%%C2+COEFS_B%%C2))
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_2=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_2=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_3(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_3) COEFS_A, COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_3

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
     $ +SUM(ABS(COEFS_A%%C2-COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3-COEFS_B%%C3))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))+SUM(ABS(COEFS_A%%C2+COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3+COEFS_B%%C3
     $ ))
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_3=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_3=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_4(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_4) COEFS_A, COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_4

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
     $ +SUM(ABS(COEFS_A%%C2-COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3-COEFS_B%%C3)
     $ )+SUM(ABS(COEFS_A%%C4-COEFS_B%%C4))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))+SUM(ABS(COEFS_A%%C2+COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3+COEFS_B%%C3
     $ ))+SUM(ABS(COEFS_A%%C4+COEFS_B%%C4))
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_4=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_4=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_5(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_5) COEFS_A,COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_5

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
     $ +SUM(ABS(COEFS_A%%C2-COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3-COEFS_B%%C3)
     $ )+SUM(ABS(COEFS_A%%C4-COEFS_B%%C4))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))+SUM(ABS(COEFS_A%%C2+COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3+COEFS_B%%C3
     $ ))+SUM(ABS(COEFS_A%%C4+COEFS_B%%C4))
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_5=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_5=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END

      FUNCTION MG5_1_COMPARE_COEFS_6(COEFS_A,COEFS_B)

      USE TENS_REC
      TYPE(COEFF_TYPE_6) COEFS_A,COEFS_B
      REAL*8 COEF_CHECK_THRS
      COMMON/MG5_1_COEF_CHECK_THRS/COEF_CHECK_THRS
      REAL*8 DENOM,NUM
      LOGICAL MG5_1_COMPARE_COEFS_6

      NUM = ABS(COEFS_A%%C0-COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1-COEFS_B%%C1))
     $ +SUM(ABS(COEFS_A%%C2-COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3-COEFS_B%%C3)
     $ )+SUM(ABS(COEFS_A%%C4-COEFS_B%%C4))
      DENOM = ABS(COEFS_A%%C0+COEFS_B%%C0)+SUM(ABS(COEFS_A%%C1+COEFS_B%%C1
     $ ))+SUM(ABS(COEFS_A%%C2+COEFS_B%%C2))+SUM(ABS(COEFS_A%%C3+COEFS_B%%C3
     $ ))+SUM(ABS(COEFS_A%%C4+COEFS_B%%C4))
      IF(DENOM.GT.0D0)THEN
        MG5_1_COMPARE_COEFS_6=((NUM/DENOM).LT.COEF_CHECK_THRS)
      ELSE
        MG5_1_COMPARE_COEFS_6=(NUM.LT.COEF_CHECK_THRS)
      ENDIF

      END


      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_0(ML_COEFS,GOLEM_COEFS)
      USE PRECISION_GOLEM, ONLY: KI
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      COMPLEX(KI) GOLEM_COEFS
      GOLEM_COEFS=ML_COEFS(0)
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_1(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_1
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_1) GOLEM_COEFS
C     Constant coefficient 
      GOLEM_COEFS%%C0=ML_COEFS(0)
C     Coefficient q(0)
      GOLEM_COEFS%%C1(1,1)=-ML_COEFS(1)
C     Coefficient q(1)
      GOLEM_COEFS%%C1(2,1)=-ML_COEFS(2)
C     Coefficient q(2)
      GOLEM_COEFS%%C1(3,1)=-ML_COEFS(3)
C     Coefficient q(3)
      GOLEM_COEFS%%C1(4,1)=-ML_COEFS(4)
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_2(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_2
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_2) GOLEM_COEFS
C     Constant coefficient 
      GOLEM_COEFS%%C0=ML_COEFS(0)
C     Coefficient q(0)
      GOLEM_COEFS%%C1(1,1)=-ML_COEFS(1)
C     Coefficient q(0)^2
      GOLEM_COEFS%%C1(1,2)= ML_COEFS(5)
C     Coefficient q(1)
      GOLEM_COEFS%%C1(2,1)=-ML_COEFS(2)
C     Coefficient q(1)^2
      GOLEM_COEFS%%C1(2,2)= ML_COEFS(7)
C     Coefficient q(2)
      GOLEM_COEFS%%C1(3,1)=-ML_COEFS(3)
C     Coefficient q(2)^2
      GOLEM_COEFS%%C1(3,2)= ML_COEFS(10)
C     Coefficient q(3)
      GOLEM_COEFS%%C1(4,1)=-ML_COEFS(4)
C     Coefficient q(3)^2
      GOLEM_COEFS%%C1(4,2)= ML_COEFS(14)
C     Coefficient q(0)*q(1)
      GOLEM_COEFS%%C2(1,1)= ML_COEFS(6)
C     Coefficient q(0)*q(2)
      GOLEM_COEFS%%C2(2,1)= ML_COEFS(8)
C     Coefficient q(0)*q(3)
      GOLEM_COEFS%%C2(3,1)= ML_COEFS(11)
C     Coefficient q(1)*q(2)
      GOLEM_COEFS%%C2(4,1)= ML_COEFS(9)
C     Coefficient q(1)*q(3)
      GOLEM_COEFS%%C2(5,1)= ML_COEFS(12)
C     Coefficient q(2)*q(3)
      GOLEM_COEFS%%C2(6,1)= ML_COEFS(13)
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_3(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_3
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_3) GOLEM_COEFS
C     Dummy routine for MG5_1_FILL_GOLEM_COEFS_3
      STOP 'ERROR: 3 > 2'
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_4(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_4
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_4) GOLEM_COEFS
C     Dummy routine for MG5_1_FILL_GOLEM_COEFS_4
      STOP 'ERROR: 4 > 2'
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_5(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_5
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_5) GOLEM_COEFS
C     Dummy routine for MG5_1_FILL_GOLEM_COEFS_5
      STOP 'ERROR: 5 > 2'
      END

      SUBROUTINE MG5_1_FILL_GOLEM_COEFFS_6(ML_COEFS,GOLEM_COEFS)
      USE TENS_REC, ONLY: COEFF_TYPE_6
      INCLUDE 'coef_specs.inc'
      INCLUDE 'loop_max_coefs.inc'
      COMPLEX*16 ML_COEFS(0:LOOPMAXCOEFS-1)
      TYPE(COEFF_TYPE_6) GOLEM_COEFS
C     Dummy routine for MG5_1_FILL_GOLEM_COEFS_6
      STOP 'ERROR: 6 > 2'
      END
